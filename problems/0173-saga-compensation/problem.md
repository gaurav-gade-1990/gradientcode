Your travel agent books a trip as a sequence of side-effecting tool calls: reserve the hotel, charge the card, send the confirmation. If a step fails, the steps that already happened must be undone in reverse order. The worker process can also die at any moment, and a new worker must pick the saga up from its journal without double charging or leaving a stray reservation.

Implement two functions with the same signature:

```python
run_saga(saga_id, steps, services, journal, clock, max_comp_attempts=3) -> status
resume_saga(saga_id, steps, services, journal, clock, max_comp_attempts=3) -> status
```

`run_saga` starts with an empty journal. `resume_saga` is called by a fresh worker after a crash, with the same journal. Only the journal survives a crash, so keep no state anywhere else.

**Services** (from the judge):

- `services.do(step, idempotency_key)` performs the step and returns its result, a booking id string. It raises `ToolError` when the step is declined. The key must be `saga_id + ":" + step`. Calling it again with the same key returns the same result without doing the work twice.
- `services.undo(step, result)` compensates a completed step, using the result `do` returned. It may raise `ServerError` (transient). Undoing a step that is already undone is a no-op.

**Journal.** `journal.append(record)` stores a dict durably; `journal.records()` returns all records in order. Append exactly these records:

| when | record |
|---|---|
| before the first `do` of a step | `{"type": "step_started", "step": s}` |
| `do` returned `r` | `{"type": "step_done", "step": s, "result": r}` |
| `do` raised `ToolError` `e` | `{"type": "step_failed", "step": s, "error": str(e)}` |
| before the first `undo` of a step | `{"type": "comp_started", "step": s}` |
| `undo` succeeded | `{"type": "comp_done", "step": s}` |
| `undo` failed `max_comp_attempts` times in this run | `{"type": "comp_failed", "step": s, "attempts": max_comp_attempts}` |
| the end | `{"type": "saga_finished", "status": status}` |

**Forward.** Run the steps in order. If one fails, stop going forward and compensate.

**Compensation.** Undo every step that has a `step_done` record, in **reverse** order. Never undo a step that failed or never ran. Retry an `undo` that raises `ServerError`: before retry `k` (`k = 0` first) call `clock.sleep(2 ** k)`. Don't sleep after the last attempt. A step whose undo is exhausted gets `comp_failed`, and you move on to the next step.

**Status.** `"completed"` if every step succeeded, `"stuck"` if any step has a `comp_failed` record, otherwise `"compensated"`. Return it.

**Resume rules.**

- A journal that already has `saga_finished` returns its status and calls nothing.
- A `step_started` with no outcome: call `do` again with the same key, and don't append another `step_started`.
- A `comp_started` with no outcome: call `undo` again with a fresh budget of `max_comp_attempts`, and don't append another `comp_started`.
- Never call `do` or `undo` for a step whose outcome is already journaled.

The judge first runs the saga with no crash. Then, for **every** service call `n` in that run, it reruns the scenario with a crash just **before** call `n` and again just **after** it (the side effect happened but your code never saw the return value). It then calls `resume_saga` and checks the invariants: each step's side effect happened at most once, the compensations ran in reverse order, no step was undone that never ran, the undo retries stayed in budget, the final state matches the status, and the journal ends with exactly one `saga_finished`. The crash is a `BaseException`, so don't catch it.

**Constraints**

- `1 <= len(steps) <= 5`, distinct step names.
- `1 <= max_comp_attempts <= 4`.
- Catch only `ToolError` from `do` and `ServerError` from `undo`. Don't import `time`.
