## 1. What the problem is really asking

A fulfillment workflow reserves stock, charges a card, books a shipment and emails the customer. The worker running it can die between any two of those steps. If the restarted worker simply runs the workflow again from the top, the customer is charged twice. Your job is the engine that makes a restart safe: **replay what already happened from a log, and only run live what never happened.**

Under the story, this is **memoization by sequence number, with a consistency check**. The workflow is ordinary Python written as a generator. Each `yield` is a command, "run this activity with these args". Your engine numbers the commands `0, 1, 2, ...`:

- If the history already has an event at that number, the command was done in an earlier run. Hand the workflow the recorded result (or raise the recorded error) without calling anything.
- If it doesn't, call the activity for real, write the event to history **at once**, then hand the result back.
- If the recorded event isn't the same command, the code changed under a running workflow. Stop with `NonDeterminismError`.

This is the core loop of Temporal, Cadence and Azure Durable Functions.

The judge runs your function once per entry in `runs`, all against the **same** history list, crashing some runs on purpose. For each run it records the outcome (`returned`, `WorkerCrash` or `NonDeterminismError`), the result, and every live activity call. At the end it records the final history. So the graded things are: which side effects really happened, in which run, and what the durable log looks like.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `workflow` | a generator function, e.g. `order_v1` | `gen = workflow(wf_input)` |
| `wf_input` | the order dict (`id`, `sku`, `amount`, `email`, `card_limit`) | pass it to `workflow`, nothing else |
| a yielded command | a tuple `(activity_name, args)` | `name, args = cmd` |
| `history` | the durable list of events, possibly empty | read `history[seq]`; `append` new events to **this list** |
| an event | `{"seq", "activity", "args", "status", "result"}` or `... "status": "failed", "error"}` | replay its `result`, or raise `ToolError(event["error"])` |
| `activities` | `{name: fn}`; `fn(**args)` returns a result or raises `ToolError` | only called for commands past the end of history |

Here is `order_v1` from the driver. Read it, because you'll be driving it:

```python
def order_v1(order):
    res = yield ("reserve_inventory", {"order_id": order["id"], "sku": order["sku"]})
    try:
        charge = yield ("charge_card", {"order_id": order["id"], "amount": order["amount"]})
    except ToolError as e:
        yield ("release_inventory", {"reservation": res})
        return {"status": "payment_failed", "error": str(e)}
    tracking = yield ("create_shipment", {"order_id": order["id"], "reservation": res})
    yield ("send_email", {"to": order["email"], "template": "shipped", "tracking": tracking})
    return {"status": "shipped", "charge": charge, "tracking": tracking}
```

Three details are easy to miss:

- **A failure has to be raised *inside* the workflow**, at the `yield` that asked for the activity, so its `try/except` can compensate. `gen.send(value)` can't do that; `gen.throw(error)` can.
- **The return value arrives as an exception.** When the generator finishes, `gen.send` raises `StopIteration`, and the workflow's `return` value is `stop.value`.
- **"Crash" is the driver raising `WorkerCrash` from inside an activity call.** With `crash_at = k`, the run dies just before its k-th *live* call; replayed steps don't count. You don't catch it: the problem says to let it propagate. All that matters is what was already in `history` when it happened.

## 3. Trace Example 2 by hand

Two runs of `order_v1` against one empty history. Run 1 has `crash_at = 3`.

**Run 1.**

| seq | command | in history? | action | history length after |
|---|---|---|---|---|
| 0 | `reserve_inventory` | no | live call 1, returns `res_A-1182`, append event 0 | 1 |
| 1 | `charge_card` amount 84 | no | live call 2, returns `ch_A-1182`, append event 1 | 2 |
| 2 | `create_shipment` | no | live call 3: the driver raises `WorkerCrash` | 2 |

Outcome `WorkerCrash`, live calls `reserve_inventory` and `charge_card`. The history survived with two events because each was appended the moment its activity returned.

**Run 2.** A brand-new generator, the same history.

| seq | command | in history? | action |
|---|---|---|---|
| 0 | `reserve_inventory` | yes, matches | send `"res_A-1182"` back, no call |
| 1 | `charge_card` | yes, matches | send `"ch_A-1182"` back, **no second charge** |
| 2 | `create_shipment` | no | live, returns `1ZA-1182`, append event 2 |
| 3 | `send_email` | no | live, returns `sent shipped`, append event 3 |
| end | `StopIteration` | seq 4 = len 4 | return `{"status": "shipped", "charge": "ch_A-1182", "tracking": "1ZA-1182"}` |

Run 2's live calls are only `create_shipment` and `send_email`. Notice that the workflow code is identical in both runs; it can't tell a replayed result from a live one. That's the whole trick: it re-derives `res`, `charge` and `tracking` from the history and arrives at exactly the state it had when the worker died.

**Example 3: a deploy changed the code.** The history holds three `order_v1` events (reserve, charge, shipment), and the run uses `order_v2`, which sends a "confirmed" email before shipping. Seq 0 and seq 1 replay. At seq 2 the code asks for `send_email` but the history recorded `create_shipment`. Outcome `NonDeterminismError`, with **zero** live calls. If you fed the recorded result anyway, the email step would receive `"1ZA-1182"` as its result and the shipment step would then run for real a second time.

**The trickiest hidden case, "recorded failure is replayed, not retried".** The card limit is 50, so the charge of 84 is declined. Run 1 (`crash_at = 3`): reserve runs live, charge runs live and raises `ToolError("card_declined: insufficient funds")`, the engine appends a `failed` event and throws the error into the workflow, the workflow's `except` asks for `release_inventory`, and that's live call 3, so the worker dies. Run 2: seq 0 replays, seq 1 is a **failed** event, so the engine throws `ToolError("card_declined: insufficient funds")` into the workflow without calling `charge_card`; the workflow compensates; `release_inventory` runs live. Run 2's only live call is `release_inventory`, and it returns `{"status": "payment_failed", "error": "card_declined: insufficient funds"}`.

## 4. Key idea: write the event before resuming the workflow

The live branch is "call, append, then resume", in that order. If you collect new events in a local list and write them to `history` only when the workflow finishes, a crash throws away everything the run did. In Example 2 the second run would then find an empty history and charge the card again. The event log is the only thing that survives the crash, so every completed side effect has to be in it before your code does anything else.

(In production there's still a tiny window: the activity can succeed and the process die before the append. That's why durable engines promise *at-least-once* activities, and side-effecting ones carry idempotency keys.)

## 5. Key idea: check the command, not just the position

Replaying by position alone looks right and passes the happy-path tests. It breaks the moment the code changes. The check has two parts:

- **The activity name** catches inserted, removed or reordered steps (Example 3).
- **The canonical args** catch the same step called with different inputs. In "args changed is nondeterminism" the order amount is now 99 but the recorded charge was for 84. Replaying `ch_A-1182` would tell the workflow the customer paid 99 when they paid 84.

"Canonical" means `json.dumps(args, sort_keys=True)`. Recorded args may have their keys in a different order from what the code yields: the test's `H_CHG` event stores `{"amount": ..., "order_id": ...}` while `order_v1` yields `order_id` first. Without `sort_keys`, "finished workflow replays with zero calls" and "key order in recorded args" both raise `NonDeterminismError` on a perfectly good history.

There's a mirror-image check at the end: if the workflow returns while `seq < len(history)`, the history holds events the code no longer produces. In "history longer than workflow", `order_no_email` dropped the shipping email, so it finishes after three commands while the history has four. That must be an error too, or a deploy that silently skips a step looks like success.

## 6. Plan before you code

```
gen = workflow(wf_input); seq = 0; value = None; error = None
loop:
    resume the generator: throw(error) if the last step failed, else send(value)
    if it finished (StopIteration):
        if seq < len(history): raise NonDeterminismError   # leftover events
        return stop.value
    name, args = the command; clear value and error
    if seq < len(history):                                   # replay
        rec = history[seq]
        if name or canonical args differ: raise NonDeterminismError
        completed -> value = rec.result ; failed -> error = ToolError(rec.error)
    else:                                                    # live
        try: value = activities[name](**args); append completed event
        except ToolError e: append failed event; error = e
    seq += 1
```

| situation | activity called? | history written? | workflow receives |
|---|---|---|---|
| replay, completed event matches | no | no | the recorded `result` |
| replay, failed event matches | no | no | `ToolError(event["error"])` raised at the `yield` |
| replay, mismatch | no | no | nothing: `NonDeterminismError` |
| live, success | yes | completed event | the result |
| live, `ToolError` | yes | failed event with `str(e)` | the same error raised at the `yield` |
| live, `WorkerCrash` (or anything else) | it raised | no | nothing: it propagates |

## 7. Build it one piece at a time

**Step 1: drive the generator.** The first resume must be `send(None)`; that's what starting a generator requires, and `value` starts as `None`. After a failed step you `throw` instead, so the workflow's `except ToolError` runs.

```python
def run_workflow(workflow, wf_input, history, activities):
    gen = workflow(wf_input)
    seq, value, error = 0, None, None
    while True:
        try:
            cmd = gen.throw(error) if error is not None else gen.send(value)
        except StopIteration as stop:
            return stop.value
        name, args = cmd
        value, error = None, None
        ...
        seq += 1
```

Clearing `value, error` right after reading the command matters: an error from step 1 must not be thrown again at step 2.

**Step 2: the live branch.** Append to `history` itself (the driver passes the durable store, and later runs read the same list). Store `str(e)` as the error, since that's what replay rebuilds the `ToolError` from.

```python
        else:
            try:
                value = activities[name](**args)
                history.append({"seq": seq, "activity": name, "args": args, "status": "completed", "result": value})
            except ToolError as e:
                history.append({"seq": seq, "activity": name, "args": args, "status": "failed", "error": str(e)})
                error = e
```

Catch only `ToolError`. `WorkerCrash` must escape: it simulates the process dying, and nothing after it can run.

**Step 3: the replay branch.** Check first, then feed. A failed event becomes a raised error, not a fresh call.

```python
        if seq < len(history):
            rec = history[seq]
            if rec["activity"] != name or _canon(rec["args"]) != _canon(args):
                raise NonDeterminismError("step %d: history has %s, workflow asked for %s" % (seq, rec["activity"], name))
            if rec["status"] == "completed":
                value = rec["result"]
            else:
                error = ToolError(rec["error"])
```

**Step 4: the leftover-history check.** Put it inside the `StopIteration` handler, before returning.

```python
        except StopIteration as stop:
            if seq < len(history):
                raise NonDeterminismError("workflow finished but history has %d more events" % (len(history) - seq))
            return stop.value
```

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# Canonical args: the same dict always serializes to the same string, whatever its key order.
import json

# The one failure type activities raise on purpose, and the one we record and replay.
from gc_runtime import ToolError


# Raised when the code no longer matches the history it is replaying.
class NonDeterminismError(Exception):
    pass  # no extra behaviour; the type itself is the signal


# Turn args into a comparable string; sort_keys makes key order irrelevant.
def _canon(x):
    return json.dumps(x, sort_keys=True)  # the comparison the problem defines


# Drive one run of the workflow against the durable history.
def run_workflow(workflow, wf_input, history, activities):
    gen = workflow(wf_input)  # a fresh generator: the workflow starts from its first line
    # seq numbers the commands; value/error is what the next resume hands the workflow.
    seq, value, error = 0, None, None
    # One iteration per command the workflow yields.
    while True:
        # Resume the workflow and get its next command.
        try:
            # A failed step is raised at the yield so the workflow's except can compensate.
            cmd = gen.throw(error) if error is not None else gen.send(value)
        # The workflow returned.
        except StopIteration as stop:
            # Recorded events the code never asked for: a deploy removed a step.
            if seq < len(history):
                # Fail loudly rather than report success for a run that skipped recorded steps.
                raise NonDeterminismError("workflow finished but history has %d more events" % (len(history) - seq))
            return stop.value  # the workflow's return value is the run's result
        name, args = cmd  # every command is (activity_name, args)
        value, error = None, None  # forget the last step's outcome before handling this one
        # This command already ran in an earlier attempt: replay it.
        if seq < len(history):
            rec = history[seq]  # the event recorded for this position
            # Same position but a different command means the code changed: refuse to guess.
            if rec["activity"] != name or _canon(rec["args"]) != _canon(args):
                # Stop before feeding a result to the wrong step or calling anything.
                raise NonDeterminismError("step %d: history has %s, workflow asked for %s" % (seq, rec["activity"], name))
            # It succeeded last time.
            if rec["status"] == "completed":
                value = rec["result"]  # hand back the recorded result; the activity is not called
            # It failed last time.
            else:
                error = ToolError(rec["error"])  # re-raise the recorded failure; never retry it
        # Past the end of the history: this command has never run.
        else:
            # Run the side effect for real.
            try:
                value = activities[name](**args)  # a WorkerCrash here propagates, as it should
                # Make it durable before the workflow continues, so a crash right after can't lose it.
                history.append({"seq": seq, "activity": name, "args": args, "status": "completed", "result": value})
            # The activity reported a failure.
            except ToolError as e:
                # A failure is history too; record it so replay reproduces it.
                history.append({"seq": seq, "activity": name, "args": args, "status": "failed", "error": str(e)})
                error = e  # and raise it into the workflow on the next resume
        seq += 1  # the next command gets the next number
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | 4 live calls, history of 4 completed events | the live branch appends one event per activity |
| Example 2 | run 1 crashes after 2 calls; run 2 runs only `create_shipment` and `send_email` | replay from history, no second charge |
| Example 3 | `NonDeterminismError`, 0 live calls | the activity-name check |
| args changed is nondeterminism | `NonDeterminismError` at the charge, 0 live calls | the canonical-args check |
| payment declined live | live calls reserve, charge, release; result `payment_failed` | a live `ToolError` is recorded as failed and thrown into the workflow |
| recorded failure is replayed, not retried | run 2's only live call is `release_inventory` | a failed event is re-raised, not re-run |
| finished workflow replays with zero calls, key order in recorded args | full replay with no calls; key-order history replays seq 0 and runs the rest live | `sort_keys=True` in `_canon` |
| history longer than workflow | `NonDeterminismError`, 0 live calls | the leftover-history check |
| compatible deploy after early crash | `order_v2` replays seq 0 and 1, then runs 3 activities live; history ends with 5 events | a code change past the end of the history is fine |
| crash before first activity | run 1 makes no calls; run 2 runs all 4 live | an empty history after a crash is just a fresh start |
| three crashes then finish | live calls per run: reserve; charge; none; shipment and email | each crash keeps exactly what was appended before it |

## 10. Complexity

One run does O(C) steps for C commands, plus `json.dumps` on each replayed command's args, so O(C · a) where a is the size of the args. History grows by one event per live activity. Across repeated crashes the replayed prefix is re-walked every time, so k restarts cost O(k · C), which is nothing next to the cost of a real activity.

At scale, the cost that matters is the history itself. A long-running agent that loops for hours can accumulate thousands of events, and every restart replays all of them. Temporal caps this with "continue-as-new", which starts a fresh run with a small summary as input. The history also has to be stored durably (a database row per event, written synchronously), and that write latency is paid on every live activity.

## 11. If you got Wrong Answer

Compare each run's `activity_calls` first; they show which side effects happened.

- **Run 2 of "Example 2" calls `reserve_inventory` and `charge_card` again.** Either you rerun from the top and never replay, or you buffer events and write them to `history` only when the workflow returns, so the crash lost them.
- **"Example 3" returns `shipped` instead of `NonDeterminismError`, and `create_shipment` shows up as a live call.** You replay by position without comparing the activity name and args: the new email step was handed the recorded tracking number, and the shipment was booked a second time.
- **"args changed is nondeterminism" returns normally.** You compare names but not args.
- **"finished workflow replays with zero calls" or "key order in recorded args" raises `NonDeterminismError`.** You compare `json.dumps(args)` without `sort_keys=True`.
- **"history longer than workflow" returns `shipped`.** You don't check for leftover events when the workflow finishes.
- **"recorded failure is replayed, not retried" shows `charge_card` in run 2.** You call the activity again for a failed event instead of raising its recorded error.
- **"payment declined live" returns `shipped` with `"charge": None` and never calls `release_inventory`.** You `send(None)` after a failure instead of `throw(error)`, so the workflow's `except` never runs and it ships an unpaid order.
- **Outcome `ToolError` instead of `returned`.** You let the live `ToolError` escape `run_workflow` instead of recording it and throwing it into the workflow.

## 12. Follow-ups an interviewer might ask

- *How do you deploy a change to a workflow while old runs are still in flight?* Version the code path. Temporal's `patched()` / `GetVersion` records a marker in history: old histories take the old branch, and new runs take the new one. Without it, every in-flight run of `order_v1` would fail like Example 3.
- *Why can't the workflow call `time.time()` or `random()` directly?* Replay would get a different value than the original run and take a different branch. Anything non-deterministic must go through an activity or an SDK call (`workflow.now()`) so it is recorded and replayed like everything else.
- *The activity succeeded but the worker died before the append. What then?* The activity runs again on restart, so it's at-least-once. Give side-effecting activities an idempotency key such as workflow id plus seq, and let the payment provider deduplicate (problem 119).
- *How would you undo the reservation and charge if shipping fails for good?* Run compensating activities in reverse order, which is a saga (problem 173, saga-compensation). The workflow's `except` around `charge_card` is a one-step version of that.
- *How does this apply to agents?* A long-running agent is a workflow whose activities are model calls and tool calls. Recording them lets it resume after a crash or a human pause without repeating paid model calls; see problem 110 (human-approval-gates) and problem 106 (plan-and-execute-replan).
