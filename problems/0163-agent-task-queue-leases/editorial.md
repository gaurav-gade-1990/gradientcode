## Approach

Model each task as a small state machine and make time lazy but exact.

```
ready --lease--> leased --ack--> done
  ^                |
  +---- expire / nack (deliveries < max)
                   +---- expire / nack (deliveries == max) --> dead (DLQ)
```

**Lazy expiry.** There is no background thread. Every public method first expires every lease with `deadline <= now`, in deadline order. Because every observation goes through a method, the queue behaves exactly as if a timer had fired at each deadline, and the log shows the expiry before whatever triggered it.

**Lease ids name deliveries.** `f"{task}#{n}"` is unique per delivery, so validity is one comparison: is this the task's *current* lease and is the task still leased? A crashed worker that wakes up holding `#1` while `#2` is out is stale by construction. This is the fencing-token idea.

**Idempotent ack.** Check "already done" first. A worker that retries its ack after a network blip gets `"duplicate"` and nothing is logged twice. Only then check the current lease, so a zombie's ack on a task someone else holds is `"stale"`.

**One release path.** Expiry and nack both call `release`: back to ready at the task's original position, or to the DLQ once it has been delivered `max_deliveries` times. Sharing the code keeps the two paths from drifting apart.

## Common mistakes

- **Leases that never expire.** A worker OOMs mid-task and the task is invisible forever. Nothing errors; the customer's invoice just never reconciles.
- **`<` instead of `<=` at the deadline.** For an instant two workers can both believe they own the task.
- **Accepting a zombie's ack.** The task is marked done with the old worker's half-finished result while the new worker is still running it, and its real result is thrown away.
- **Logging a retried ack as a second completion.** Billing and metrics count the task twice.
- **Dead-lettering one delivery late.** A poison message that crashes every worker gets one more chance to take down the fleet.
- **Heartbeats that revive an expired lease.** The task has already been handed to someone else, and now two workers hold it.

## Production notes

- SQS (visibility timeout, `ChangeMessageVisibility` as the heartbeat, `maxReceiveCount` redrive to a DLQ), Google Cloud Tasks and Pub/Sub ack deadlines, and Temporal activity heartbeats with `heartbeat_timeout` all implement this contract.
- Leases give at-least-once delivery, never exactly-once. The work itself must be idempotent, or keyed by task id downstream (`idempotent-tool-execution`). If a stale worker can still write, pass the lease id as a fencing token to the storage layer and reject older tokens there.
- Choose the visibility timeout from the p99 task duration, and heartbeat at a fraction of it (a third is common). Long agent tasks with LLM calls should heartbeat between steps, not just at the end.
- Alert on DLQ depth and keep the failure reason with each dead task; redrive tooling (replay from the DLQ after a fix) is part of the design, not an afterthought.
- Pairs with `ai-coworker-inbox-triage` (who should take the task) and `durable-workflow-replay` (resuming a long task without redoing finished steps).
