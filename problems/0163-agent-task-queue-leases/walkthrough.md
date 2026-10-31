## 1. What the problem is really asking

A worker takes a task, and the queue can't tell whether it's working, stalled, or dead. The answer SQS and Cloud Tasks use is a **lease**: the task is hidden from other workers until a deadline. If the worker acks before the deadline, the task is done. If it doesn't, the task comes back and someone else gets it. A worker can **heartbeat** to push its deadline out, and a task that keeps failing goes to a **dead-letter queue** after `max_deliveries` tries.

Under the story this is a **state machine per task** with four states, plus one rule about time:

```
ready --lease--> leased --ack--> done
  ^                |
  +-- expire/nack -+  (deliveries < max)
                   +-- expire/nack --> dead   (deliveries == max)
```

There's no background timer. Every public method starts by expiring every lease whose deadline has passed, so the queue behaves as if a timer had fired. The judge replays timed operations from several workers and grades **every return value, every log entry with its time, and the DLQ**. Most of the difficulty is in the order of checks and log entries, not the data structure.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `clock` | a `gc_runtime.Clock` | `clock.now()` is the only source of time; the driver advances it before each op |
| `log` | a `gc_runtime.EventLog` | `log.append(kind, **fields)` stamps `t` with `clock.now()` for you |
| `visibility_timeout` | how long a lease lasts, default `30.0` | deadline is `now + visibility_timeout` on lease and on heartbeat |
| `max_deliveries` | `1` to `5`, default `3` | a released task whose delivery count has reached this goes to the DLQ |
| `priority` | `0` is most urgent | ready tasks are served by `(priority, enqueue order)` |
| `lease_id` | `f"{task_id}#{n}"`, the `n`th delivery | names one delivery, so an old one is automatically not current |

The driver is short. Each op runs at virtual time `at`, and acks, nacks and heartbeats use either a literal lease id or the id that an earlier `lease()` call returned:

```python
clock.advance(op["at"] - clock.now())
...
out = getattr(q, kind)(lease)
results.append(out)
return {"results": results, "events": [dict(e) for e in log.entries], "dlq": list(q.dead_letters())}
```

Four details are easy to miss:

- **Expiry is `deadline <= now`, not `<`.** At exactly the deadline the lease is already gone.
- **Expired leases are logged at the time of the call that noticed them**, not at the deadline, because `EventLog` stamps `clock.now()`. An `expired` entry always appears just before the entry of whatever call triggered the sweep.
- **A requeued task keeps its enqueue position.** You don't give it a new place at the back.
- **Calls that fail quietly log nothing.** `False`, `"duplicate"`, `"stale"`, and `lease()` returning `None` add no event.

## 3. Trace the examples by hand

**Example 1** shows priority and the duplicate ack. `inv-1182` (P1) is enqueued before `contract-7` (P0), but P0 wins:

| t | op | returns | events |
|---|---|---|---|
| 1 | `lease(coworker-a)` | `contract-7#1`, delivery 1 | `leased` until 31.0 |
| 2 | `lease(coworker-b)` | `inv-1182#1` | `leased` until 32.0 |
| 10 | `ack(contract-7#1)` | `"acked"` | `acked` by coworker-a |
| 11 | `ack(contract-7#1)` | `"duplicate"` | none |
| 12 | `ack(inv-1182#1)` | `"acked"` | `acked` by coworker-b |

**Example 2** is the whole lease lifecycle:

| t | op | returns | events |
|---|---|---|---|
| 0 | `lease(coworker-a)` | `inv-1182#1` | `leased` until 30.0 |
| 20 | `heartbeat(inv-1182#1)` | `True` | `extended` until 50.0 |
| 45 | `lease(coworker-b)` | `None` | none: still leased |
| 50 | `lease(coworker-b)` | `inv-1182#2`, delivery 2 | `expired` (coworker-a, delivery 1), then `leased` until 80.0 |
| 55 | `ack(inv-1182#1)` | `"stale"` | none |
| 56 | `ack(inv-1182#2)` | `"acked"` | `acked` by coworker-b |

At t=50 the sweep runs first. The deadline 50.0 is `<= 50`, so the lease expires, the task goes back to ready, and the same `lease()` call hands it to coworker-b. Both entries carry `t: 50.0`, `expired` first. At t=55 coworker-a comes back from the dead with `#1`, but the current lease is `#2`, so its ack is stale.

**Example 3** (`max_deliveries=2`) is two crashes in a row. At t=30, `lease(w2)` first expires `#1` (delivery 1 < 2, so it's ready again), then leases `#2`. At t=60 the `sweep` expires `#2`. The delivery count is now 2, which has reached `max_deliveries`, so the task is dead: `expired`, then `dead_lettered` with `reason: "max_deliveries"`. `lease(w3)` at t=61 returns `None`, and the DLQ is `["eval-run-3"]`.

**The trickiest hidden case, "several expire in one sweep"** (`visibility_timeout=10`): `p0` is leased at 0 (deadline 10) and heartbeated at 5 (deadline 15). `p1` and `p2` are leased at 1 (deadline 11). The sweep at 40 finds all three past due and expires them in `(deadline, enqueue order)`: `p1` (11, enqueued 1st), `p2` (11, enqueued 3rd), then `p0` (15). Sorting by enqueue order alone gives `p1, p0, p2`, and the event log no longer matches. At 41 the three re-leases go out by priority, `p0, p1, p2`, and the fourth `lease` gets `None`.

## 4. Key idea: lazy expiry, done the same way everywhere

You could keep a timer per lease, but the judge has no threads and no wall clock. Instead, every public method begins with the same `_sweep()`. Since nothing can observe the queue except through a method, the queue looks exactly as if each lease had expired on time. The catch is that it has to be **every** method. In "heartbeat after expiry", the worker heartbeats `t#1` at t=31, one second after its deadline. The sweep at the top of `heartbeat` expires it first, so `_current` no longer finds a live lease and the heartbeat returns `False`. Skip the sweep in `heartbeat` and that call revives a dead lease, the next `lease()` finds nothing ready, and two workers end up believing they own the task.

## 5. Key idea: a lease id is a fencing token

The lease id `task#n` names a single delivery. The task record stores only its *current* lease id, so "is this lease valid?" is one comparison: the task exists, is in state `leased`, and `t["lease"] == lease_id`. A zombie holding `#1` while `#2` is out fails that test without any special case. In "zombie ack after redelivery is ready", the task isn't even leased when the zombie acks at t=31 (the sweep at 30 put it back to ready), and the answer is still `"stale"`.

`ack` checks **"already done" first**. Once a task is done, any ack for it, from the worker that finished it or from a zombie, is `"duplicate"`. In "zombie ack while re-leased", the zombie's `refund-9#1` at t=35 is `"stale"` (w2 holds `#2`), but the same id at t=37, after w2 acked, is `"duplicate"`.

## 6. Plan before you code

```
task record: id, priority, payload, seq (enqueue order), state, deliveries, lease, worker, deadline

_sweep():   for each leased task with deadline <= now, sorted by (deadline, seq):
                log expired; _release(task)
_release(t): clear lease/worker/deadline
             if deliveries >= max: state dead, append to DLQ, log dead_lettered
             else: state ready (seq unchanged)
_current(lease_id): the task if it is leased and its current lease == lease_id, else None

every public method: _sweep() first, then:
  enqueue:   known id -> False; else add ready, log enqueued, True
  lease:     no ready -> None; else min by (priority, seq), deliveries += 1, set lease/deadline, log leased
  heartbeat: not current -> False; else deadline = now + vt, log extended, True
  ack:       done -> "duplicate"; not current -> "stale"; else log acked, mark done, "acked"
  nack:      not current -> "stale"; else log nacked, _release, "dead_lettered" or "requeued"
```

| call | condition | returns | logs |
|---|---|---|---|
| `ack` | task done | `"duplicate"` | nothing |
| `ack` | current lease | `"acked"` | `acked` |
| `ack` | anything else | `"stale"` | nothing |
| `nack` | current lease, deliveries < max | `"requeued"` | `nacked` |
| `nack` | current lease, deliveries == max | `"dead_lettered"` | `nacked`, `dead_lettered` |

## 7. Build it one piece at a time

**Step 1: the record and the release path.** Expiry and nack both call `_release`, so they can't disagree about when a task dies. The test is `>=`: a task delivered `max_deliveries` times has had all its chances.

```python
    def _release(self, t):
        t["lease"] = t["worker"] = t["deadline"] = None
        if t["deliveries"] >= self.max:
            t["state"] = "dead"
            self.dlq.append(t["id"])
            self.log.append("dead_lettered", task=t["id"], reason="max_deliveries")
        else:
            t["state"] = "ready"
```

Note that `seq` isn't touched. That's what "keeps its enqueue position" means: in "requeued task keeps its place", `a` is nacked at t=4 and is still served before `b` and `c`.

**Step 2: the sweep.** Collect first, then sort, then release. Sorting by `(deadline, seq)` gives the order the spec asks for when several leases have expired since the last call.

```python
    def _sweep(self):
        now = self.clock.now()
        due = [t for t in self.tasks.values() if t["state"] == "leased" and t["deadline"] <= now]
        for t in sorted(due, key=lambda t: (t["deadline"], t["seq"])):
            self.log.append("expired", task=t["id"], worker=t["worker"], delivery=t["deliveries"])
            self._release(t)
```

Log `expired` *before* `_release`, because `_release` clears `worker` and may log `dead_lettered`, which has to come second.

**Step 3: finding the current lease.** Task ids contain no `#`, so splitting on the last `#` recovers the task id. A lease id for a task that never existed (`ghost#1`) just finds no record.

```python
    def _current(self, lease_id):
        task_id = lease_id.rsplit("#", 1)[0]
        t = self.tasks.get(task_id)
        if t is not None and t["state"] == "leased" and t["lease"] == lease_id:
            return t
        return None
```

**Step 4: lease and ack.** `lease` increments the delivery count before building the id, so the first lease is `#1`. `ack` logs while `worker` is still set, then clears it.

```python
    def lease(self, worker):
        self._sweep()
        ready = [t for t in self.tasks.values() if t["state"] == "ready"]
        if not ready:
            return None
        t = min(ready, key=lambda t: (t["priority"], t["seq"]))
        t["deliveries"] += 1
        ...

    def ack(self, lease_id):
        self._sweep()
        t = self.tasks.get(lease_id.rsplit("#", 1)[0])
        if t is not None and t["state"] == "done":
            return "duplicate"
        t = self._current(lease_id)
        if t is None:
            return "stale"
        self.log.append("acked", task=t["id"], worker=t["worker"])
        ...
```

## 8. Full solution

```python
class TaskQueue:  # leased task queue: visibility timeout, heartbeats, redelivery, DLQ
    def __init__(self, clock, log, visibility_timeout=30.0, max_deliveries=3):  # one queue per run
        self.clock, self.log = clock, log  # virtual time and the graded event log
        self.vt, self.max = visibility_timeout, max_deliveries  # lease length and delivery cap
        self.tasks = {}   # id -> record
        self.seq = 0  # enqueue counter: the FIFO tie-break within a priority
        self.dlq = []  # dead task ids, in the order they died

    # ------------------------------------------------------------ helpers
    def _sweep(self):  # lazy expiry: make the queue look as if timers had fired on time
        now = self.clock.now()  # the only source of time
        # every lease whose deadline has arrived (<=: at the deadline the lease is already gone)
        due = [t for t in self.tasks.values() if t["state"] == "leased" and t["deadline"] <= now]
        for t in sorted(due, key=lambda t: (t["deadline"], t["seq"])):  # earliest deadline first, ties by enqueue order
            # log before releasing, while worker is still set and before any dead_lettered entry
            self.log.append("expired", task=t["id"], worker=t["worker"], delivery=t["deliveries"])
            self._release(t)  # back to ready, or to the DLQ

    def _release(self, t):  # the one path shared by expiry and nack
        t["lease"] = t["worker"] = t["deadline"] = None  # nobody holds it now; old lease ids go stale
        if t["deliveries"] >= self.max:  # it has had every delivery it's allowed
            t["state"] = "dead"  # stop handing out a task that keeps failing
            self.dlq.append(t["id"])  # park it for a human to inspect
            self.log.append("dead_lettered", task=t["id"], reason="max_deliveries")  # record why
        else:  # it still has deliveries left
            t["state"] = "ready"  # seq is unchanged, so it keeps its place in line

    def _current(self, lease_id):  # the task this lease id currently holds, or None
        task_id = lease_id.rsplit("#", 1)[0]  # "inv-1182#2" -> "inv-1182"
        t = self.tasks.get(task_id)  # None for an id that was never enqueued
        if t is not None and t["state"] == "leased" and t["lease"] == lease_id:  # live, and this exact delivery
            return t  # the caller really holds the task
        return None  # unknown task, not leased, or an older delivery (a zombie)

    # ------------------------------------------------------------ API
    def enqueue(self, task_id, priority, payload):  # add a task once, ever
        self._sweep()  # every public method expires due leases first
        if task_id in self.tasks:  # seen before, in any state, even done or dead
            return False  # idempotent enqueue: do nothing and log nothing
        self.seq += 1  # this task's place in line
        # a fresh ready task with no deliveries yet
        self.tasks[task_id] = {"id": task_id, "priority": priority, "payload": payload, "seq": self.seq, "state": "ready",
                               "deliveries": 0, "lease": None, "worker": None, "deadline": None}
        self.log.append("enqueued", task=task_id, priority=priority)  # record the arrival
        return True  # it was added

    def lease(self, worker):  # hand the most urgent ready task to a worker
        self._sweep()  # expired leases become ready before we look
        ready = [t for t in self.tasks.values() if t["state"] == "ready"]  # the candidates
        if not ready:  # nothing to give out
            return None  # quiet: no log entry
        t = min(ready, key=lambda t: (t["priority"], t["seq"]))  # P0 first, then enqueue order
        t["deliveries"] += 1  # this is delivery n
        t["state"], t["worker"] = "leased", worker  # hidden from other workers now
        t["lease"] = "%s#%d" % (t["id"], t["deliveries"])  # the id names this delivery only
        t["deadline"] = self.clock.now() + self.vt  # it comes back if not acked by then
        # record who has it and until when
        self.log.append("leased", task=t["id"], worker=worker, delivery=t["deliveries"], until=t["deadline"])
        return {"task": t["id"], "lease_id": t["lease"], "delivery": t["deliveries"], "payload": t["payload"]}  # the worker's ticket

    def heartbeat(self, lease_id):  # a live worker asks for more time
        self._sweep()  # an already-expired lease must not be revived
        t = self._current(lease_id)  # only the current, unexpired lease counts
        if t is None:  # stale, expired or unknown
            return False  # quiet refusal
        t["deadline"] = self.clock.now() + self.vt  # a full timeout from now
        self.log.append("extended", task=t["id"], until=t["deadline"])  # record the new deadline
        return True  # extended

    def ack(self, lease_id):  # a worker reports the task finished
        self._sweep()  # a lease that just expired can't be acked
        t = self.tasks.get(lease_id.rsplit("#", 1)[0])  # look the task up by id, whatever the delivery
        if t is not None and t["state"] == "done":  # a retried or late ack after completion
            return "duplicate"  # idempotent: never count a task twice
        t = self._current(lease_id)  # is this the delivery that's out right now?
        if t is None:  # a zombie's old lease, or an unknown task
            return "stale"  # reject it so it can't overwrite the real worker's result
        self.log.append("acked", task=t["id"], worker=t["worker"])  # log while worker is still set
        t["state"], t["lease"], t["worker"], t["deadline"] = "done", None, None, None  # finished for good
        return "acked"  # completed

    def nack(self, lease_id):  # a worker gives the task back
        self._sweep()  # expire first, so a late nack is stale
        t = self._current(lease_id)  # only the current holder may give it back
        if t is None:  # not the current lease
            return "stale"  # quiet refusal
        self.log.append("nacked", task=t["id"], worker=t["worker"])  # log before release clears worker
        self._release(t)  # same path as expiry: ready again, or dead
        return "dead_lettered" if t["state"] == "dead" else "requeued"  # tell the worker which happened

    def sweep(self):  # the driver's way to let time pass with no other call
        self._sweep()  # just the expiry step

    def dead_letters(self):  # read the DLQ
        return list(self.dlq)  # a copy, so the caller can't edit our state
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | P0 `contract-7` leased first; second ack `"duplicate"`, no log | `(priority, seq)` ordering and the done-first ack check |
| Example 2 | `None` at 45, delivery 2 at 50, zombie `"stale"` at 55 | heartbeat, `<=` expiry inside `lease`, fencing by lease id |
| Example 3 | `expired` + `dead_lettered` at 60, DLQ `["eval-run-3"]` | the sweep, and `>=` against `max_deliveries` |
| empty queue | `None`, `"stale"`, `"stale"`, `False`, no events | unknown lease ids, and quiet calls log nothing |
| duplicate enqueue | `False` both times, even after the task is done | the id is remembered in any state |
| nack until dead | `requeued`, `requeued`, `dead_lettered`, then `"stale"` | nack shares the release path; a dead task's lease is stale |
| requeued task keeps its place | `a` again before `b` and `c` | `seq` unchanged on release |
| expiry exactly at deadline | heartbeat `False` and ack `"stale"` at t=30 | `deadline <= now` |
| heartbeat after expiry | `False` at 31; `t#1` ack at 91 is `"duplicate"` | heartbeat sweeps first and can't revive a lease |
| zombie ack while re-leased | `"stale"` at 35, `"acked"` at 36, `"duplicate"` at 37 | stale vs duplicate depends on whether the task is done |
| zombie ack after redelivery is ready | `"stale"` while the task is ready | `_current` needs state `leased` |
| several expire in one sweep | expired order `p1, p2, p0`; fourth lease `None` | sorted by `(deadline, seq)` |
| max_deliveries 1 | nack returns `"dead_lettered"`; expiry dead-letters too; DLQ `["once", "twice"]` | the smallest cap |
| chaos, chaos with short leases | random leases, heartbeats, acks and nacks from four workers | every rule at once |

## 10. Complexity

Each call scans all tasks for the sweep and for ready tasks, so a call is O(T log T) with T tasks (the sort is only over the leases that are due). At 300 operations that's nothing. A real queue keeps two heaps: ready tasks keyed by `(priority, seq)` and leased tasks keyed by `(deadline, seq)`. Then `lease` is O(log T) and the sweep pops only what's due, O(k log T) for k expiries. The event log grows by at most two entries per call. In production, the visibility timeout is chosen from the p99 task duration, and long agent tasks heartbeat between LLM steps, often at a third of the timeout.

## 11. If you got Wrong Answer

- **Example 2's lease at t=50 returns `None`, and "expiry exactly at deadline" accepts the heartbeat at t=30.** You expire with `deadline < now`. Use `<=`.
- **Leases never come back; Example 2's second worker never gets the task.** Your methods don't run the sweep at all, or the sweep never releases.
- **"heartbeat after expiry" returns `True` at t=31.** `heartbeat` doesn't sweep first, so it extends a lease that has already expired.
- **Example 3's DLQ is empty, and "nack until dead" returns `"requeued"` on the third nack.** You dead-letter when `deliveries > max`. Compare with `>=`.
- **Example 1 logs a second `acked` at t=11.** Check "already done" before anything else, and return `"duplicate"` without logging.
- **"zombie ack while re-leased" returns `"acked"` at t=35.** You accept any lease id for the task. Compare it with the task's *current* lease id.
- **"several expire in one sweep" logs `p1, p0, p2`.** You expire in enqueue order. Sort by `(deadline, seq)`.
- **"requeued task keeps its place" gives `b` to w2.** You put the released task at the back of the line. Keep its original `seq`.

## 12. Follow-ups an interviewer might ask

- *Does this give exactly-once processing?* No, at-least-once. A worker can finish the work and crash before acking, and the task runs again. Make the work idempotent or key its side effects by task id (problem 119, idempotent-tool-execution covers this pattern for tool calls).
- *The zombie's ack is rejected, but it already wrote half a result to the database. Now what?* Pass the lease id to the storage layer as a fencing token and have it reject writes with an older delivery number. The queue alone can only stop the ack.
- *How would you pick which worker should take a task, not just which task goes next?* That's a matching problem over skills, load and deadlines (problem 164, ai-coworker-inbox-triage).
- *A long task crashed after step 7 of 10. Does redelivery redo all ten?* With durable workflow replay, the next worker replays a journal of finished steps and resumes at step 8 (problem 111, durable-workflow-replay).
- *What do you do with the DLQ?* Alert on its depth, store the failure reason with each dead task, and build redrive tooling to replay tasks once the bug is fixed. SQS calls the cap `maxReceiveCount` and the move a "redrive".
