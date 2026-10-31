## 1. What the problem is really asking

Some tool calls are too risky to run on the model's say-so. A refund moves money and a deleted account doesn't come back, so compliance wants a person to click "Approve" first. Your job is the controller that sits between the agent and its tools: it lets safe calls through, refuses forbidden ones, and parks risky ones until a human decides.

Under the story, this is a **two-state machine with one slot and a FIFO queue**:

- **running**: nothing is waiting for a human. Calls are processed as they arrive.
- **paused**: one call sits in the pending slot. Every new call goes to the back of the queue.

Three things move it from paused back to running: an authorized `approve`, an authorized `reject`, or the approval **expiring**. Each time it resumes, the queue is drained through the *same* policy that a brand-new call goes through.

The judge doesn't look at your internal fields. It records three things: every event you `log.append`, every real `execute` call (tool, args and time), and your `state` after each operation. So the order and the exact fields of your events are what's graded.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `policy["approval_required"]` | tools that need a human, e.g. `issue_refund`, `delete_account` | a set; a match parks the call |
| `policy["blocked"]` | tools that never run, e.g. `wire_transfer` | a set; a match logs `denied` |
| `policy["approvers"]` | user ids allowed to decide, e.g. `lead.maria`, `lead.omar` | a set; anyone else is `not_authorized` |
| `ttl` | seconds an approval request stays open | `expires_at = now + ttl` |
| `clock` | a `gc_runtime.Clock` the driver advances between operations | `clock.now()` for expiry checks |
| `execute(tool, args)` | the real side effect; returns `"<tool> ok"` | call it exactly once per call that should run |
| `log` | a `gc_runtime.EventLog` | `log.append(kind, **fields)`; it stamps `t` for you |

The driver is short, and it tells you how you're graded:

```python
for op in ops:
    clock.advance(op["t"] - clock.now())
    ...dispatch to r.call / r.approve / r.reject / r.tick...
    states.append(r.state)
```

Three details are easy to miss:

- **Nothing runs on its own.** There's no timer thread. Time only moves when the driver advances the clock before an operation, so expiry has to be checked *lazily*, at the start of every method. That's why `tick()` exists: it's an operation that does nothing but the expiry check.
- **`state` is a property**, not a method. The driver reads `r.state` with no parentheses.
- **The deadline is exclusive.** The rule is `now >= expires_at`. At exactly `t = expires_at` the request is already gone.

## 3. Trace Example 1 by hand

`ttl = 300`. Four operations: a safe call, a refund, an email, then Maria approves.

| op | t | what happens | events logged | state after |
|---|---|---|---|---|
| `call c1 get_order` | 0 | running, not blocked, not risky: execute | `executed c1 get_order "get_order ok"` | running |
| `call c2 issue_refund` | 10 | risky: park it, `expires_at = 10 + 300` | `approval_requested c2 expires_at=310` | paused |
| `call c3 send_email` | 20 | paused, so queue it | `queued c3 send_email` | paused |
| `approve c2 lead.maria` | 65 | 65 < 310, c2 is pending, Maria is an approver | `approved c2`, `executed c2 issue_refund`, `executed c3 send_email` | running |

The last row is where the work is. Approving logs `approved`, runs the refund (`executed c2`), clears the slot, and then **drains**: the queue holds `c3`, which goes through the policy, is safe, and runs at the same time `t = 65`. The `executed` list the judge records is `get_order` at 0, then `issue_refund` and `send_email` both at 65.

**Example 3: the boundary.** `ttl = 60`, so the refund requested at 10 expires at 70.

| op | t | expiry check | events | state |
|---|---|---|---|---|
| `call c2 issue_refund` | 10 | nothing pending | `approval_requested c2 expires_at=70` | paused |
| `tick` | 69 | 69 >= 70? no | none | paused |
| `tick` | 70 | 70 >= 70? **yes** | `expired c2` | running |
| `approve c2 lead.maria` | 71 | nothing pending | `ignored c2 not_pending` | running |

The refund never runs. The hidden case "approve exactly at expiry" drops the ticks and approves at `t = 70`: the expiry check inside `approve` fires first, logs `expired c2`, and then the approval finds nothing pending, so you get `expired` followed by `ignored ... not_pending`, both at `t = 70`. In "approve just before expiry" the approval lands at 69.5 and goes through.

**The trickiest hidden case, "queued risky call pauses again".** `ttl = 100`. The refund c2 is pending; `delete_account` c3 and `get_order` c4 arrive and are queued. At `t = 20` Omar approves c2:

```
approved c2 lead.omar
executed c2 issue_refund
approval_requested c3 delete_account expires_at=120    <- the drain hit a risky call
```

The drain pops c3, runs it through the policy, and the policy parks it with a fresh deadline of `20 + 100 = 120`. The run is paused again, so the drain **stops** and c4 stays in the queue. Only when Maria approves c3 at `t = 30` do you see `executed c3` and then `executed c4`. The states after each operation are `paused, paused, paused, paused, running`.

## 4. Key idea: the drain goes through the policy, not around it

It's tempting to write the drain as "run everything in the queue":

```python
while self.queue:
    self._run(self.queue.pop(0))      # wrong
```

That executes a queued `delete_account` with no approval and a queued `wire_transfer` that's blocked outright. The call was risky when the model asked for it; it's no less risky because it waited in line. So there's one function, `_process`, that decides blocked / risky / safe, and *both* entry paths use it: `call` when the run is running, and `_drain` when the run resumes. The drain loop's condition, `while self.pending is None and self.queue`, is what stops it when a queued call pauses the run again.

## 5. Key idea: "is it pending right now?" makes approvals idempotent

An approval is only valid for the call in the pending slot *at this moment*. Checking `self.pending["id"] == call_id` gives you three behaviours for free:

- **A double-click** (or a retried Slack webhook) arrives after the slot has been cleared, so it's `not_pending` and the refund isn't executed twice.
- **A stale approval** for a call that expired finds nothing pending.
- **A typo'd or wrong id** is ignored and the real request stays paused.

If instead you keep a table of every request ever made and look the id up there, a second approval re-executes the call. That's the bug in "duplicate approve does not re-execute".

## 6. Plan before you code

```
__init__: three sets from policy; pending = None; queue = []
state: "paused" if pending else "running"

_expire():  if pending and now >= pending.expires_at:
                log expired; pending = None; drain
_process(c): blocked -> log denied
             approval_required -> pending = c + expires_at; log approval_requested
             else -> execute; log executed
_drain():   while pending is None and queue: _process(queue.pop(0))

call:     expire; if pending: queue + log queued, else _process
approve:  expire; check pending id, then approver; log approved; execute; drain
reject:   expire; same checks; log rejected; drain
tick:     expire
```

The decision table for `approve` and `reject`, checked in this order:

| situation | event | state |
|---|---|---|
| `call_id` is not the pending call (or nothing is pending) | `ignored {id, reason: "not_pending"}` | unchanged |
| `approver` not in `approvers` | `ignored {id, reason: "not_authorized"}` | still paused |
| otherwise, approve | `approved`, then `executed`, then whatever the drain logs | running, unless the drain pauses |
| otherwise, reject | `rejected`, then whatever the drain logs | running, unless the drain pauses |

## 7. Build it one piece at a time

**Step 1: state and the policy sets.** Turn the lists into sets once. `state` is derived from `pending` so it can never disagree with it.

```python
class ApprovalRun:
    def __init__(self, policy, ttl, clock, execute, log):
        self.needs_approval = set(policy.get("approval_required", []))
        self.blocked = set(policy.get("blocked", []))
        self.approvers = set(policy.get("approvers", []))
        self.ttl, self.clock, self.execute, self.log = ttl, clock, execute, log
        self.pending = None
        self.queue = []

    @property
    def state(self):
        return "paused" if self.pending else "running"
```

**Step 2: one policy function.** The blocked check comes first, so a tool listed in both sets would be denied rather than offered for approval. The deadline is computed when the call is *processed*, not when it was queued. That's why the queued `delete_account` above expires at 120, not 111.

```python
    def _run(self, c):
        result = self.execute(c["tool"], c["args"])
        self.log.append("executed", id=c["id"], tool=c["tool"], result=result)

    def _process(self, c):
        if c["tool"] in self.blocked:
            self.log.append("denied", id=c["id"], tool=c["tool"])
        elif c["tool"] in self.needs_approval:
            c = dict(c, expires_at=self.clock.now() + self.ttl)
            self.pending = c
            self.log.append("approval_requested", id=c["id"], tool=c["tool"], expires_at=c["expires_at"])
        else:
            self._run(c)
```

Note the order inside `_run`: execute first, then log `executed` with the real result string.

**Step 3: drain and expire.** Expiry drains too. In "expiry noticed by next call drains queue" (`ttl = 30`), the refund expires at 40 while an email waits in the queue. Nothing happens until the next call at `t = 50`, which first logs `expired c2`, then drains (`executed c3 send_email`), and only then processes its own call (`executed c4 get_order`).

```python
    def _drain(self):
        while self.pending is None and self.queue:
            self._process(self.queue.pop(0))

    def _expire(self):
        if self.pending and self.clock.now() >= self.pending["expires_at"]:
            self.log.append("expired", id=self.pending["id"])
            self.pending = None
            self._drain()
```

**Step 4: the public methods.** Every one starts with `_expire()`. `approve` and `reject` share the checks in `_decide`, which hands back the call and clears the slot only when both checks pass.

```python
    def call(self, call_id, tool, args):
        self._expire()
        c = {"id": call_id, "tool": tool, "args": args}
        if self.pending:
            self.queue.append(c)
            self.log.append("queued", id=call_id, tool=tool)
        else:
            self._process(c)

    def _decide(self, call_id, approver):
        self._expire()
        if self.pending is None or self.pending["id"] != call_id:
            self.log.append("ignored", id=call_id, reason="not_pending")
            return None
        if approver not in self.approvers:
            self.log.append("ignored", id=call_id, reason="not_authorized")
            return None
        c, self.pending = self.pending, None
        return c
```

In `approve`, run the approved call *before* draining. The approved refund was asked for first, so it executes before the queued email.

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# One controller per agent run: it sits between the model's tool calls and the real tools.
class ApprovalRun:
    # policy: the three tool/user lists; ttl: seconds an approval stays open; log: the graded trail.
    def __init__(self, policy, ttl, clock, execute, log):
        # Sets, built once, so every policy lookup is O(1).
        self.needs_approval = set(policy.get("approval_required", []))
        self.blocked = set(policy.get("blocked", []))  # these tools never run
        self.approvers = set(policy.get("approvers", []))  # the only users whose decisions count
        # Keep the collaborators; the clock is advanced by the driver, never by us.
        self.ttl, self.clock, self.execute, self.log = ttl, clock, execute, log
        self.pending = None  # the one call waiting for a human, or None
        self.queue = []  # calls that arrived while paused, oldest first

    # The driver reads r.state with no parentheses, so this must be a property.
    @property
    def state(self):  # "paused" or "running", as the judge records it
        # Derived from the slot, so it can never disagree with it.
        return "paused" if self.pending else "running"

    # Actually run a tool and record it.
    def _run(self, c):
        result = self.execute(c["tool"], c["args"])  # the real side effect happens here
        # Log after executing so the event carries the real result string.
        self.log.append("executed", id=c["id"], tool=c["tool"], result=result)

    # The single policy path, used by fresh calls and by queued calls during a drain.
    def _process(self, c):
        # Blocked wins over everything: these never run and never reach a human.
        if c["tool"] in self.blocked:
            self.log.append("denied", id=c["id"], tool=c["tool"])  # refused, not executed
        # Risky tool: park it in the slot and wait for a human.
        elif c["tool"] in self.needs_approval:
            # The deadline starts now, when it is processed, not when it was queued.
            c = dict(c, expires_at=self.clock.now() + self.ttl)
            self.pending = c  # this pauses the run
            # Tell the approver what is waiting and until when.
            self.log.append("approval_requested", id=c["id"], tool=c["tool"], expires_at=c["expires_at"])
        # Any other tool is safe.
        else:
            self._run(c)  # run it straight away

    # Resume: feed queued calls back through the policy until one pauses the run again.
    def _drain(self):
        # Stop as soon as a queued risky call takes the slot.
        while self.pending is None and self.queue:
            self._process(self.queue.pop(0))  # oldest first, same rules as a fresh call

    # Lazy expiry: nothing wakes up on its own, so every entry point checks the deadline first.
    def _expire(self):
        # >=: at exactly expires_at the request is already gone.
        if self.pending and self.clock.now() >= self.pending["expires_at"]:
            self.log.append("expired", id=self.pending["id"])  # record that it timed out
            self.pending = None  # the call is dropped, never executed
            self._drain()  # the run resumes, so queued calls get their turn

    # The agent wants to run a tool.
    def call(self, call_id, tool, args):
        self._expire()  # a stale approval must not keep this call waiting
        c = {"id": call_id, "tool": tool, "args": args}  # the call as we store it
        # Something is waiting for a human, so this call waits its turn.
        if self.pending:
            self.queue.append(c)  # FIFO keeps the agent's order
            self.log.append("queued", id=call_id, tool=tool)  # record that it is waiting
        # Running: decide right now.
        else:
            self._process(c)  # blocked, risky or safe

    # Shared checks for approve and reject; returns the call only if this decision is valid.
    def _decide(self, call_id, approver):
        self._expire()  # a late click on an expired request must find nothing pending
        # Only the call pending right now can be decided; this makes a double-click harmless.
        if self.pending is None or self.pending["id"] != call_id:
            self.log.append("ignored", id=call_id, reason="not_pending")  # stale, wrong or duplicate
            return None  # nothing changes
        # Someone outside the approvers list (the agent's own bot, for example).
        if approver not in self.approvers:
            self.log.append("ignored", id=call_id, reason="not_authorized")  # run stays paused
            return None  # nothing changes
        c, self.pending = self.pending, None  # take the call and free the slot
        return c  # the caller decides what to do with it

    # A human said yes.
    def approve(self, call_id, approver):
        c = self._decide(call_id, approver)  # None if the decision doesn't count
        # Only act on a valid decision.
        if c is not None:
            self.log.append("approved", id=call_id, approver=approver)  # who signed off
            self._run(c)  # the approved call was asked for first, so it runs before the queue
            self._drain()  # then resume the queued calls

    # A human said no.
    def reject(self, call_id, approver):
        c = self._decide(call_id, approver)  # same checks as approve
        # Only act on a valid decision.
        if c is not None:
            self.log.append("rejected", id=call_id, approver=approver)  # who refused
            self._drain()  # resume without executing the rejected call

    # An operation that only lets time catch up.
    def tick(self):
        self._expire()  # the expiry check and nothing else
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | refund and queued email both execute at t=65 | queue while paused, approve runs the call, then the drain |
| Example 2 | `ignored not_authorized`, then `rejected`, then `denied`; nothing executed | the approvers set, reject without executing, the blocked set |
| Example 3 | `expired c2` at t=70, late approval `not_pending` | `>=` at the boundary, and `tick()` runs the expiry check |
| approve exactly at expiry | `expired` then `ignored not_pending`, both at t=70 | expiry is checked *before* the approval is considered |
| approve just before expiry | approved and executed at t=69.5 | the deadline isn't off by one the other way |
| duplicate approve does not re-execute | second approve at t=21 is `not_pending`; one refund executed | approvals match only the current pending call |
| queued risky call pauses again | c3 gets `expires_at=120`; c4 waits until t=30 | drain uses `_process` and stops when the run pauses |
| queued blocked call denied on drain | after the reject: `denied c3 wire_transfer`, `executed c4 send_email` | queued calls still hit the blocked check |
| expiry noticed by next call drains queue | at t=50: `expired`, `executed c3`, `executed c4` | expiry inside `call`, and expiry drains before the new call |
| approve wrong id | `ignored c9 not_pending`; c2 still pending and later approved | a wrong id doesn't clear the slot |
| approve when nothing pending | `ignored c1 not_pending` | `pending is None` is handled |
| expired then re-requested | old id c2 is `not_pending`; new id c6 approved and executed at t=43 | an expired approval can't be revived by a later click |

## 10. Complexity

Each operation does O(1) work for the policy lookups (set membership) plus the drain. A drain can process many queued calls, but each call is popped once, so across a whole run the total work is O(number of operations). `self.queue.pop(0)` is O(queue length) on a Python list; with at most 20 operations it doesn't matter, and in production you'd use `collections.deque.popleft()`.

The real cost at scale isn't CPU. A paused run holds its state for minutes or hours while a human looks at Slack, usually across process restarts and on whichever server receives the webhook. So `pending` and `queue` must live in durable storage, not in memory, and the expiry has to be checked lazily like here (or by a scheduled sweeper), because no in-process timer survives a deploy.

## 11. If you got Wrong Answer

Compare the `events` lists. The first event that differs points to the bug:

- **"Example 2" shows `approved c2 agent.bot` and an execution.** You never check `approver in self.approvers`.
- **"approve exactly at expiry" executes the refund.** Your expiry test is `>` instead of `>=`.
- **No `expired` event anywhere, and "expiry noticed by next call drains queue" never runs the email.** Expiry isn't implemented, or it isn't called at the start of `call`.
- **"Example 3" has no `expired` at t=70.** `tick()` doesn't run the expiry check.
- **"queued risky call pauses again" executes `delete_account` without an `approval_requested`, or "queued blocked call denied on drain" executes the wire transfer.** Your drain calls `execute` directly instead of `_process`.
- **"duplicate approve does not re-execute" has two `issue_refund` executions.** You look approvals up in a table of past requests rather than comparing with the current pending call.
- **In "Example 1" the email executes before the refund, or not at all.** You drain before running the approved call, or you forgot to drain after approving.

## 12. Follow-ups an interviewer might ask

- *The human answers two hours later, after a deploy. How does the run survive?* Persist the pending call and the queue keyed by run id, and resume from that record when the approval arrives. LangGraph does this with `interrupt()` plus a checkpointer; problem 111 (durable-workflow-replay) covers resuming by replaying a recorded history.
- *The agent changes the refund amount after approval. How do you stop that?* Hash the exact tool name and arguments into the approval, show the approver those arguments, and refuse to execute if the hash no longer matches.
- *How do you make the approval callback safe against forgery and retries?* Sign it and make it idempotent by call id (problem 167, signed-webhook-delivery). The "is it pending right now?" check already makes a retried callback harmless.
- *Why only one pending approval at a time?* It keeps the agent's actions in order: a later call might depend on the refund's result. If calls are independent, you could keep one slot per call and let safe calls run past a paused one, but the ordering guarantee is gone.
- *Where should the policy come from?* A real policy engine with per-tenant rules and limits, like "refunds over $100 need approval" (problem 160), with every decision written to a tamper-evident audit log (problem 161).
