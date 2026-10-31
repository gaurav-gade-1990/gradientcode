AI coworkers on your platform pull long-running tasks (reconcile an invoice, draft a contract, re-run an eval) from a shared queue. Workers crash, stall, and sometimes come back from the dead minutes later and try to report a result. Build the queue the way SQS and Cloud Tasks do: leases with a visibility timeout, heartbeats, redelivery, a dead-letter queue and idempotent acks.

`TaskQueue(clock, log, visibility_timeout=30.0, max_deliveries=3)` gets a `gc_runtime.Clock` and an `EventLog`. Read time only from `clock.now()`. Record state transitions with `log.append(kind, **fields)`, which stamps each entry with the current time.

A task is in one state: **ready**, **leased**, **done** or **dead** (in the DLQ). Ready tasks are served by lowest `priority` number first (P0 before P1), then in enqueue order. A task keeps its enqueue position when it returns to ready.

**Expiry.** At the start of **every** method below, expire each leased task whose lease deadline is `<= clock.now()`, in order of `(deadline, enqueue order)`: log `expired`, then **release** it. To release a task: if its delivery count has reached `max_deliveries`, it becomes dead, is appended to the DLQ and logs `dead_lettered`; otherwise it becomes ready.

| method | behavior | returns |
|---|---|---|
| `enqueue(task_id, priority, payload)` | If the id was ever enqueued (any state), do nothing. Else add it as ready and log `enqueued`. | `True` / `False` |
| `lease(worker)` | Take the first ready task, increment its delivery count `n`, set the lease id to `f"{task_id}#{n}"` and the deadline to `now + visibility_timeout`, log `leased`. | `{"task", "lease_id", "delivery", "payload"}`, or `None` if nothing is ready |
| `heartbeat(lease_id)` | If it is the task's current, unexpired lease, set the deadline to `now + visibility_timeout` and log `extended`. | `True` / `False` |
| `ack(lease_id)` | If the task is already done: `"duplicate"`. Else if it is the current lease: mark done, log `acked`, `"acked"`. Else `"stale"`. | string |
| `nack(lease_id)` | If it is the current lease: log `nacked`, then release the task. Else `"stale"`. | `"requeued"`, `"dead_lettered"` or `"stale"` |
| `sweep()` | Only the expiry step. | `None` |
| `dead_letters()` | | DLQ task ids in the order they died |

Calls that return `False`, `"duplicate"` or `"stale"`, or `lease` returning `None`, log nothing.

**Events**, with exactly these fields:

| kind | fields |
|---|---|
| `enqueued` | `task`, `priority` |
| `leased` | `task`, `worker`, `delivery`, `until` |
| `extended` | `task`, `until` |
| `expired` | `task`, `worker`, `delivery` |
| `nacked` | `task`, `worker` |
| `acked` | `task`, `worker` |
| `dead_lettered` | `task`, `reason` (always `"max_deliveries"`) |

The judge replays timed operations from several workers, including crashed workers that never ack and zombies that ack after their lease expired, and grades every return value, the full event log with times, and the DLQ.

**Constraints**

- At most 300 operations; times are non-decreasing.
- `1 <= max_deliveries <= 5`, `visibility_timeout > 0`.
- Task ids contain no `#`. Any `lease_id` passed in has the form `f"{task_id}#{n}"`, though the task may not exist.
