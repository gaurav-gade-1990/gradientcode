Your support agent can issue refunds and delete accounts, and compliance wants a human to sign off on those. Write the run controller that pauses the agent on risky tool calls and resumes it when a human decides.

`ApprovalRun(policy, ttl, clock, execute, log)` gets:

- `policy`: `{"approval_required": [tools], "blocked": [tools], "approvers": [user ids]}`. Any other tool runs automatically.
- `ttl`, how many seconds an approval request stays open.
- `clock`, a `gc_runtime.Clock`, and `execute(tool, args)`, which actually runs a tool and returns a result string.
- `log`, a `gc_runtime.EventLog`. Record events with `log.append(kind, **fields)`; it stamps each one with `clock.now()`.

The run is `"paused"` while an approval is pending and `"running"` otherwise; expose this as the `state` property. At most one approval is pending at a time.

**Expiry first.** At the start of **every** method below, if a call is pending and `clock.now() >= expires_at`, log `expired {id}`, clear it, and drain the queue.

**Processing a call** (a new call while running, or a queued call during a drain):

| tool | event(s) |
|---|---|
| in `blocked` | `denied {id, tool}`; not executed |
| in `approval_required` | `approval_requested {id, tool, expires_at}` with `expires_at = now + ttl`; the run pauses |
| anything else | execute it, then `executed {id, tool, result}` |

**Methods.**

| method | behavior |
|---|---|
| `call(call_id, tool, args)` | if paused: queue it and log `queued {id, tool}`. Otherwise process it. |
| `approve(call_id, approver)` | if `call_id` isn't the pending call: `ignored {id, reason: "not_pending"}`. If `approver` isn't in `approvers`: `ignored {id, reason: "not_authorized"}` (still paused). Otherwise `approved {id, approver}`, execute it (`executed ...`), resume, and drain. |
| `reject(call_id, approver)` | same checks; then `rejected {id, approver}`, resume without executing, and drain |
| `tick()` | only the expiry check |

**Draining.** While the run is running and the queue isn't empty, pop the oldest queued call and process it. A queued risky call pauses the run again and stops the drain.

The judge replays timestamped operations and records your events, every real `execute` call, and `state` after each operation.

**Constraints**

- At most 20 operations, with non-decreasing times
- `ttl > 0`, and call ids are unique
