## 1. What the problem is really asking

A trip is three side effects in different systems: a hotel reservation, a card charge, an email. No database transaction can span them. A **saga** gets close to one anyway: run the steps in order, and if one fails, undo the ones that already happened, newest first.

The hard part isn't the undo. The worker can die at any moment, and a new worker has to finish the job from a **journal**, an append-only log that is the only thing that survives. So this is really a **state machine rebuilt from a log**:

> read every record → work out which steps are done, which are in flight, whether anything failed, which compensations are closed → continue from exactly there.

Once you see it that way, `run_saga` is just `resume_saga` on an empty journal, and you only write the logic once.

The judge grades the clean run (status, the full journal, the list of service calls, the sleeps). Then for **every** service call it reruns the scenario twice: crashing just **before** the call, and just **after** it, when the side effect has happened but your code never saw the return value. It calls `resume_saga` and records what the resume did plus any broken invariants. For Example 1 that is 3 calls × 2 phases = 6 crash runs. Each run's `resume_calls`, `resume_journal` and `resume_sleeps` must match the reference exactly, not just be "safe".

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `saga_id` | e.g. `"trip-4411"` | half of every idempotency key |
| `steps` | step names in order, e.g. `["reserve_hotel", "charge_card", "send_confirmation"]` | forward order; reversed for compensation |
| `services.do(step, key)` | performs a step, returns a booking id like `"charge_card#2"` | raises `ToolError` when declined; same key returns the same result |
| `services.undo(step, result)` | cancels a done step, given what `do` returned | may raise `ServerError`; undoing twice is a no-op |
| `journal.append(rec)`, `journal.records()` | the durable log | append intent and outcome; replay on start |
| `clock.sleep(s)` | virtual sleep, recorded by the judge | backoff between undo retries |
| `max_comp_attempts` | undo attempts per step per run | the retry budget |

Three details are easy to miss:

- **The key is `saga_id + ":" + step` and nothing else.** No attempt counter, no UUID. A crash "after `do`" means the card was charged but you never got the booking id. The only safe recovery is to call `do` again with the *same* key and let the provider hand back the stored result.
- **A failed step never happened.** `charge_card declined` has nothing to refund. Compensate only steps with a `step_done` record.
- **The crash is a `BaseException`.** Catch only `ToolError` around `do` and `ServerError` around `undo`. Anything broader swallows the crash or hides real bugs.

## 3. Trace the examples by hand

**Example 3.** `send_confirmation` is declined and the first refund attempt hits a 503 (`flaky_undo: {"charge_card": 1}`).

| # | call | result | journal records appended |
|---|---|---|---|
| | | | `step_started reserve_hotel` |
| 1 | `do reserve_hotel` | `reserve_hotel#1` | `step_done reserve_hotel` |
| | | | `step_started charge_card` |
| 2 | `do charge_card` | `charge_card#2` | `step_done charge_card` |
| | | | `step_started send_confirmation` |
| 3 | `do send_confirmation` | `ToolError` | `step_failed send_confirmation` |
| | | | `comp_started charge_card` (newest done step first) |
| 4 | `undo charge_card` | `ServerError`, so `sleep(2**0)` = 1 s | none |
| 5 | `undo charge_card` | ok | `comp_done charge_card` |
| | | | `comp_started reserve_hotel` |
| 6 | `undo reserve_hotel` | ok | `comp_done reserve_hotel`, `saga_finished compensated` |

The sleeps are `[1.0]`, and the status is `"compensated"`. There are 12 crash runs (6 calls × 2), and none has a violation.

**A crash after call 2 in Example 1.** The card was charged, but the process died before `step_done charge_card` was written. The journal ends with `step_started charge_card`. The resume:

- sees `reserve_hotel` done and `charge_card` started but unresolved;
- does **not** append a second `step_started`;
- calls `do charge_card` with key `trip-4411:charge_card`, which returns `charge_card#2` again without a second charge;
- appends `step_done charge_card`, then runs `send_confirmation` normally.

So `resume_calls` is `["do charge_card", "do send_confirmation"]`, and the journal tail is `step_done charge_card, step_started send_confirmation, step_done send_confirmation, saga_finished completed`.

**The trickiest hidden case: "budget exactly enough"**, with `max_comp_attempts=4` and `flaky_undo: {"charge_card": 3, "reserve_hotel": 2}`. In the clean run the refund fails three times and succeeds on attempt 4, with sleeps 1, 2, 4. The hotel then fails twice and succeeds on attempt 3, with sleeps 1, 2. That gives sleeps `[1, 2, 4, 1, 2]`. Now crash **after call 5** (the second refund attempt). The service has already used up two of its three 503s. The journal shows `comp_started charge_card` and no outcome, so the resume undoes again with a **fresh** budget of 4. It sees one more 503, sleeps 1, then succeeds, so `resume_sleeps` is `[1.0, 1.0, 2.0]`. The backoff restarts at `2**0` in the new run because the budget is per run.

## 4. Key idea: write intent before, outcome after

Every side effect is bracketed by two journal records:

```
step_started s   →   do(s)   →   step_done s / step_failed s
comp_started s   →   undo(s) →   comp_done s / comp_failed s
```

That gives you exactly one ambiguous state per bracket: the intent is there and the outcome isn't. You can't tell whether the call landed. The design makes that ambiguity harmless by making the call **safe to repeat**: `do` through the idempotency key, `undo` because cancelling twice is a no-op. So the resume rule is the same for both: *re-issue the call, don't re-append the intent.*

| crash point | journal ends with | resume does |
|---|---|---|
| before `do s` | `step_started s` | `do s` (first real call) |
| after `do s` | `step_started s` | `do s` again, same key, same result back |
| before or after `undo s` | `comp_started s` | `undo s` again with a fresh budget |
| after the outcome record | `step_done` / `comp_done` | skip `s`; never call it again |
| after `saga_finished` | `saga_finished` | return the status, call nothing |

## 5. Key idea: compensate only what happened, newest first

```python
for s in reversed([s for s in steps if s in done]):
```

`done` holds only steps with a `step_done` record, so the failed step and the steps after it are excluded. Reversal matters because later steps depend on earlier ones. You refund the charge before you release the hotel, just as a database rolls back its most recent writes first. The judge checks that the cancellations happen in reverse booking order.

When a step fails as the very first step ("first step fails"), `done` is empty. The journal is `step_started reserve_hotel`, `step_failed reserve_hotel`, `saga_finished compensated`. "Compensated" with zero undos is correct: there was nothing to undo.

## 6. Plan before you code

```
resume_saga:
    replay records → done{step: result}, started, comp_started, comp_closed, failed, stuck
    if saga_finished seen: return its status
    if not failed:
        for each step not done:
            append step_started unless already started
            do(step, saga_id:step)
            ToolError → append step_failed, failed = True, stop
            else append step_done, record result
        if still not failed: append saga_finished completed, return
    for each done step, newest first, not already closed:
        append comp_started unless already started
        up to max_comp_attempts tries: sleep(2**k) before retry k ≥ 1
        success → comp_done; budget gone → comp_failed, stuck = True
    status = stuck ? "stuck" : "compensated"; append saga_finished
run_saga = resume_saga
```

| record seen in replay | state it sets |
|---|---|
| `step_started` | `started.add(s)` |
| `step_done` | `done[s] = result` |
| `step_failed` | `failed = True` |
| `comp_started` | `comp_started.add(s)` |
| `comp_done` | `comp_closed.add(s)` |
| `comp_failed` | `comp_closed.add(s)`, `stuck = True` |
| `saga_finished` | return its status |

## 7. Build it one piece at a time

**Step 1: replay the journal.** All state comes from here, which is why `run_saga` can just delegate.

```python
def resume_saga(saga_id, steps, services, journal, clock, max_comp_attempts=3):
    done, started, comp_started, comp_closed = {}, set(), set(), set()
    failed, stuck = False, False
    for r in journal.records():
        t, s = r["type"], r.get("step")
        if t == "saga_finished":
            return r["status"]
        ...  # the table in section 6
```

Note that `comp_failed` closes a compensation too. A step whose undo was exhausted in an earlier run is not retried on resume. Its outcome is already journaled.

**Step 2: go forward, skipping what's done.**

```python
    if not failed:
        for s in steps:
            if s in done:
                continue
            if s not in started:
                journal.append({"type": "step_started", "step": s})
            try:
                result = services.do(s, "%s:%s" % (saga_id, s))
            except ToolError as e:
                journal.append({"type": "step_failed", "step": s, "error": str(e)})
                failed = True
                break
            journal.append({"type": "step_done", "step": s, "result": result})
            done[s] = result
```

`if s not in started` is what keeps the journal free of duplicate `step_started` records after a crash. `str(e)` gives the exact message the judge expects, e.g. `"charge_card declined"`.

**Step 3: finish if nothing failed.**

```python
        if not failed:
            journal.append({"type": "saga_finished", "status": "completed"})
            return "completed"
```

**Step 4: compensate with bounded retries.**

```python
    for s in reversed([s for s in steps if s in done]):
        if s in comp_closed:
            continue
        if s not in comp_started:
            journal.append({"type": "comp_started", "step": s})
        for k in range(max_comp_attempts):
            try:
                services.undo(s, done[s])
            except ServerError:
                if k == max_comp_attempts - 1:
                    journal.append({"type": "comp_failed", "step": s, "attempts": max_comp_attempts})
                    stuck = True
                else:
                    clock.sleep(2 ** k)
                continue
            journal.append({"type": "comp_done", "step": s})
            break
```

The sleep happens in the `except` of attempt `k`, before attempt `k + 1`, so it is `2 ** k` and starts at 1. On the last attempt you journal `comp_failed` instead of sleeping, which is the "don't sleep after the last attempt" rule. Then you move on to the next step. A stuck refund must not stop you from cancelling the hotel.

## 8. Full solution

```python
from gc_runtime import ServerError, ToolError  # the only two errors we are allowed to handle


def run_saga(saga_id, steps, services, journal, clock, max_comp_attempts=3):  # fresh start
    # a new saga is a resume over an empty journal, so the logic lives in one place
    return resume_saga(saga_id, steps, services, journal, clock, max_comp_attempts)


def resume_saga(saga_id, steps, services, journal, clock, max_comp_attempts=3):  # continue from the journal
    done, started, comp_started, comp_closed = {}, set(), set(), set()  # state rebuilt from the log
    failed, stuck = False, False  # did a step fail, did an undo run out of budget
    for r in journal.records():  # replay: the journal is the only state that survives a crash
        t, s = r["type"], r.get("step")  # record kind and the step it concerns
        if t == "saga_finished":  # an earlier worker already finished
            return r["status"]  # report it and call nothing
        if t == "step_started":  # intent to run s was logged
            started.add(s)  # so don't log it again on resume
        elif t == "step_done":  # s definitely happened
            done[s] = r["result"]  # keep the booking id for a later undo
        elif t == "step_failed":  # a step was declined
            failed = True  # no more forward progress; go straight to compensation
        elif t == "comp_started":  # intent to undo s was logged
            comp_started.add(s)  # so don't log it again on resume
        elif t == "comp_done":  # s was undone
            comp_closed.add(s)  # never undo it again
        elif t == "comp_failed":  # s ran out of undo attempts in an earlier run
            comp_closed.add(s)  # its outcome is journaled, so don't retry it
            stuck = True  # the final status must say a human is needed

    if not failed:  # still going forward
        for s in steps:  # in order
            if s in done:  # finished before the crash
                continue  # never repeat a step whose outcome is journaled
            if s not in started:  # first time we reach this step
                journal.append({"type": "step_started", "step": s})  # intent before the side effect
            try:  # only a declined step is an expected failure
                result = services.do(s, "%s:%s" % (saga_id, s))  # same key every run, so a repeat is safe
            except ToolError as e:  # the step was declined
                journal.append({"type": "step_failed", "step": s, "error": str(e)})  # outcome: it never happened
                failed = True  # switch to compensation
                break  # stop going forward
            journal.append({"type": "step_done", "step": s, "result": result})  # outcome after the side effect
            done[s] = result  # available to undo if a later step fails
        if not failed:  # every step succeeded
            journal.append({"type": "saga_finished", "status": "completed"})  # close the saga
            return "completed"  # the happy path

    for s in reversed([s for s in steps if s in done]):  # undo only steps that happened, newest first
        if s in comp_closed:  # undone, or given up on, in an earlier run
            continue  # its outcome is already journaled
        if s not in comp_started:  # first time we undo this step
            journal.append({"type": "comp_started", "step": s})  # intent before the undo
        for k in range(max_comp_attempts):  # a fresh budget in every run
            try:  # only a transient 503 is an expected failure
                services.undo(s, done[s])  # cancel using the result do returned
            except ServerError:  # transient failure
                if k == max_comp_attempts - 1:  # that was the last allowed attempt
                    journal.append({"type": "comp_failed", "step": s, "attempts": max_comp_attempts})  # give up
                    stuck = True  # a booking is still live
                else:  # attempts remain
                    clock.sleep(2 ** k)  # exponential backoff before retry k + 1: 1, 2, 4 s
                continue  # next attempt, or leave the loop when the budget is spent
            journal.append({"type": "comp_done", "step": s})  # the undo succeeded
            break  # this step is finished; move to the next older one

    status = "stuck" if stuck else "compensated"  # stuck if any undo was exhausted
    journal.append({"type": "saga_finished", "status": status})  # exactly one closing record
    return status  # report the outcome
```

## 9. How the test cases map to the code

Every case also runs the crash sweep. For the reference solution, no crash run reports a violation.

| test case | expected (clean run) | what it checks |
|---|---|---|
| Example 1 | `completed`; three `do` calls; 6 crash runs | idempotency key on resume after `do` |
| Example 2 | `compensated`; calls `do hotel, do charge, undo hotel` | the failed step is not undone |
| Example 3 | `compensated`; refund retried once; sleeps `[1.0]` | reverse order plus one retry |
| stuck refund | `stuck`; three refund attempts, sleeps `[1.0, 2.0]`; hotel still cancelled | `comp_failed`, then moving on |
| first step fails | `compensated` with no undo calls | nothing done means nothing to compensate |
| five steps late failure | `compensated`; sleeps `[1.0, 2.0, 1.0]`; 24 crash runs | long chains, two flaky undos |
| budget exactly enough | `compensated`; sleeps `[1, 2, 4, 1, 2]` | `max_comp_attempts=4` used to the last attempt |
| single attempt | `stuck`; no sleeps at all | budget 1: fail at once, never sleep |
| one step saga | `completed` with one call | the smallest saga |
| two flaky undos | `stuck`; both undos fail twice; sleeps `[1.0, 1.0]` | several `comp_failed` records, status still one word |

"single attempt" has a subtle crash run. Crash **after** call 5 (the hotel undo) happens after the fake has used up its one 503. Your code never saw the error, so the resume retries, succeeds, and that run ends `compensated`. The crash sweep's expected outputs capture exactly this, which is why the outcome you journal must come only from what your code observed.

## 10. Complexity

Replay is O(R) in journal records, and R is at most about 2·n + 2·n + 1 for n steps. Forward is O(n) service calls. Compensation is O(n · max_comp_attempts) calls. Memory is O(n) for the replay sets. Virtual sleep time is at most `2**(max_comp_attempts-1) - 1` seconds per step, which is 7 s per step at the cap of 4.

In production the journal is a database table or a workflow engine's event history (Temporal, Step Functions), and replay runs on every worker start. The key risk at scale is not CPU but **stuck sagas**: each one is a live booking or an unrefunded charge, so it needs paging, a ticket with the journal attached, and a slow background retry.

## 11. If you got Wrong Answer

Most bugs only show up in `crash_runs`. Find the first entry whose `violations` or `resume_calls` differ.

- **`reserve_hotel performed 2 times` in the crash run "after call 1 (do reserve_hotel)".** Your idempotency key changes between runs, for example by including an attempt number.
- **The clean run's violations say `compensations ran in order ['reserve_hotel', 'charge_card']`.** You compensate in forward order. Use `reversed(...)`.
- **`undo of charge_card, which never ran` in Example 2.** You treat the failed step as done, or add it to `done`.
- **The crash run "before call 3 (undo reserve_hotel)" in Example 2 says `compensated but ['reserve_hotel'] still active`, with empty `resume_calls`.** You treat `comp_started` as closed. A crash mid-undo must undo again.
- **Example 3's clean status is `stuck` with no sleeps.** You don't retry `undo`. Loop up to `max_comp_attempts` with `clock.sleep(2 ** k)` between attempts.
- **No violations, but `resume_calls` in the Example 1 crash run "after call 2" is all three `do` calls, and the journal tail starts with `step_started reserve_hotel`.** You ignore the journal on resume. The providers' idempotency hides the damage here, but the journal fills with duplicate records, and a non-idempotent step such as an email would be sent twice.
- **Sleeps are `[2, 4]` instead of `[1, 2]`.** You compute the backoff as `2 ** (k + 1)` or sleep before the first attempt.

## 12. Follow-ups an interviewer might ask

- *Where would you put the email step?* Last, as the pivot. Everything before it must be compensable, and everything after it must be retryable until it succeeds. An email can't be unsent.
- *How would you get the journal write and an outgoing event into one atomic step?* A transactional outbox: put the event row in the same transaction as the journal record and relay it afterwards (problem 172, transactional-outbox).
- *What if some steps are pure computation, like an LLM call that decides the hotel?* Journal their outputs and replay them instead of re-running them, so a resumed workflow makes the same decisions (problem 111, durable-workflow-replay).
- *Why a fresh compensation budget after a crash rather than counting across runs?* The judge's rule is per run, and it mirrors how most workflow engines handle activity retries. You could persist attempt counts in the journal instead, at the cost of more records. Either way, a `stuck` saga keeps retrying slowly in the background and pages a human.
- *How do agents make tool calls safe to repeat?* The same way: derive the key from the run and step, and store the result keyed by it (problem 180, api-idempotent-create).
