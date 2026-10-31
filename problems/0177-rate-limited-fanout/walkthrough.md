## 1. What the problem is really asking

When an agent run finishes, everyone subscribed to it gets a notification over Slack, email or a webhook. Each provider allows only so many sends per second, and some sends fail. The fan-out has to keep two kinds of trouble contained:

- **Across channels:** a slow email provider must not delay Slack. Each channel gets its **own worker and its own rate limiter**.
- **Within a channel:** a webhook that keeps returning 503 must not hold up the healthy subscribers queued behind it. A failed send goes **back into the queue with a later ready time**, and the worker moves on at once.

Under the story this is **one priority queue per channel, ordered by `(ready_time, seq)`, drained by a single worker that spaces its sends by `interval`**. Retries are just items with a future ready time. Permanent errors (`BadRequestError`) are never retried.

The judge grades more than who got delivered. It records **every `send` call** as `[start_time, channel, subscriber, outcome]`, plus each `delivered` finish time, each `failed` reason and the final virtual time `t`. So the exact start time of every attempt, retries included, has to match.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `loop` | a `gc_runtime.EventLoop` over virtual time | `loop.spawn(worker(name))`, `loop.now()`, then `loop.run()` |
| `subscribers` | `[{"id", "channel"}, ...]` in subscription order | the index is the initial `seq`; group by channel |
| `channels[name]` | `{"interval", "max_attempts", "retry_delay"}` | spacing between starts, retry cap, base backoff |
| `send(sid, channel)` | a generator | `yield from send(sid, name)` takes the channel's latency, then returns or raises |
| `ToolError` | transient failure | retry later, unless this was the last allowed attempt |
| `BadRequestError` | permanent failure | `failed[sid] = "rejected"`, no retry |
| return value | `{"delivered": {sid: finish}, "failed": {sid: reason}}` | finish time is `loop.now()` right after `send` returns |

Inside a task, `yield 1.5` sleeps 1.5 virtual seconds and `yield from send(...)` runs the send in place. Three details are easy to miss:

- **The interval is measured between attempt *starts*.** `start = max(now, ready_time, last_start + interval)`, and `last_start` is set when the attempt begins, not when it ends. Retries count against the interval too, because the provider counts requests.
- **The backoff is measured from the *finish* of the failed attempt.** A retry's ready time is `finish + retry_delay * 2**(attempt - 1)`: delays of 1×, 2×, 4× the base.
- **Spawn workers in sorted channel-name order.** At `t=0` all workers start together, and the event loop runs them in spawn order. In Example 1 the first recorded attempt is the email one, because `"email" < "slack"`.

## 3. Trace Example 2 by hand

One channel, Slack: `interval = 1.0`, `max_attempts = 3`, `retry_delay = 2.0`, latency 0.25. Subscribers `ana`, `ben`, `cho`. Ana's first send fails.

Initial queue: `(0, 0, ana, 1)`, `(0, 1, ben, 1)`, `(0, 2, cho, 1)`.

| pick | item `(ready, seq, id, attempt)` | start = max(now, ready, last + 1.0) | outcome | after |
|---|---|---|---|---|
| 1 | `(0, 0, ana, 1)` | max(0, 0, none) = **0** | fail at 0.25 | queue `(0.25 + 2.0 = 2.25, 3, ana, 2)` |
| 2 | `(0, 1, ben, 1)` | max(0.25, 0, 0 + 1) = **1.0** | ok at 1.25 | ben delivered 1.25 |
| 3 | `(0, 2, cho, 1)` | max(1.25, 0, 1 + 1) = **2.0** | ok at 2.25 | cho delivered 2.25 |
| 4 | `(2.25, 3, ana, 2)` | max(2.25, 2.25, 2 + 1) = **3.0** | ok at 3.25 | ana delivered 3.25 |

The judge's output matches: `attempts = [[0, slack, ana, fail], [1, slack, ben, ok], [2, slack, cho, ok], [3, slack, ana, ok]]`, `delivered = {ben: 1.25, cho: 2.25, ana: 3.25}` and `t = 3.25`. The retry's `seq` is 3 because `next_seq` starts at `len(subscribers)`.

The thing to notice is pick 2. Ana failed, but the worker didn't wait out her 2-second backoff. Ben went at the next rate-limit slot. If the worker had slept in place, ben would have been delivered at 3.5 instead of 1.25.

**Example 3, the backoff ladder.** Webhook: `interval = 0.25`, `max_attempts = 4`, `retry_delay = 0.5`, latency 0.125.

| start | subscriber | attempt | outcome | next ready |
|---|---|---|---|---|
| 0 | hook-billing | 1 | reject | (none: `"rejected"`, never retried) |
| 0.25 | hook-crm | 1 | fail at 0.375 | 0.375 + 0.5 = 0.875 |
| 0.875 | hook-crm | 2 | fail at 1.0 | 1.0 + 1.0 = 2.0 |
| 2.0 | hook-crm | 3 | fail at 2.125 | 2.125 + 2.0 = 4.125 |
| 4.125 | hook-crm | 4 | fail at 4.25 | (none: attempt 4 = `max_attempts`, `"exhausted"`) |

Final `t = 4.25`. The second hook-crm attempt starts at 0.875, not at `last_start + interval = 0.5`. The ready time is the binding constraint there.

**The hidden case "retry interleaves with queue"** shows the retry rejoining the line. Eight webhook subscribers; `u00` fails twice, `u03` fails once and `u05` is rejected. `u00`'s first retry is ready at 0.625, but the worker sends `u01`, `u02`, ... at 0.25-second spacing. At 1.5 the queue holds `u06 (ready 0)`, `u07 (ready 0)`, `u00 (ready 0.625)` and `u03 (ready 1.375)`, so `u06` and `u07` go first (smaller ready time). `u00` retries at 2.0 and fails again. Its second retry is ready at `2.125 + 0.5 × 2 = 3.125` and delivers at 3.25.

## 4. Key idea: never sleep a backoff inside the worker

The worker is the channel's only sender. Whatever it sleeps on, everybody behind it waits for. Sleeping a retry's backoff in place (`wrong_head_of_line_retry.py`) turns one failing subscriber into a delay for the whole channel. In "two channels, both retrying", `w2` is delivered at 4.875 instead of 1, because it waits out all three of `w1`'s backoffs first.

Putting the retry back into the queue with `ready_time = finish + backoff` gives the same backoff to the failing subscriber and none to anyone else. The only sleep the worker ever does is up to the next allowed start: `yield start - loop.now()`.

## 5. Key idea: the rate limit belongs to the channel, and it spaces starts

Two things have to be per channel: the queue and `last_start`. Share `last_start` across channels (`wrong_shared_limiter_across_channels.py`) and Slack waits on email's interval. In Example 1, `ana@acme` is then delivered at 1.25 instead of 0.25, because her Slack send waits behind the email send that started at 0.

Measure the spacing from the start of the previous attempt, not its end. Provider limits count requests per second, so a send that takes 0.25 s doesn't need an extra 0.25 s of gap. Setting `last_start` after the send returns (`wrong_interval_from_finish.py`) adds the latency to every gap. In Example 1, ben then finishes at 1.5 instead of 1.25.

A side note on the queue order. You may find that sorting by `seq` alone gives the same answers on every case. Here that isn't luck. Within one channel, every original is ready at 0 and goes first, and each retry level is queued after the level below it with a longer backoff, so ready times only ever grow with `seq`. Sorting by `(ready_time, seq)` is still the rule the problem states, and it stays correct if retries ever arrive from elsewhere.

## 6. Plan before you code

```
queues[channel] = [(0.0, index, id, 1) for each subscriber on it]
next_seq = len(subscribers)

worker(channel):
    last_start = None
    while queue not empty:
        pop the smallest (ready, seq)
        start = max(now, ready, last_start + interval if any)
        sleep until start
        last_start = now
        try send
            ok             -> delivered[id] = now
            BadRequestError -> failed[id] = "rejected"
            ToolError      -> attempt == max: failed[id] = "exhausted"
                              else: push (now + delay * 2**(attempt-1), next_seq++, id, attempt+1)

spawn one worker per channel, sorted by name; loop.run(); return results
```

| outcome | recorded | queued again? |
|---|---|---|
| returns | `delivered[id] = finish` | no |
| `BadRequestError` | `failed[id] = "rejected"` | no |
| `ToolError`, attempt < max | nothing yet | yes, ready at finish + backoff |
| `ToolError`, attempt == max | `failed[id] = "exhausted"` | no |

## 7. Build it one piece at a time

**Step 1: build the queues.** The subscriber's index in the full list is its `seq`, so ties at `ready_time = 0` keep subscription order.

```python
queues = {}
for i, s in enumerate(subscribers):
    queues.setdefault(s["channel"], []).append((0.0, i, s["id"], 1))
next_seq = [len(subscribers)]
```

`next_seq` is a one-element list so every worker's closure can bump the same counter. A plain integer would need `nonlocal`.

**Step 2: pick and wait.** With at most 40 items, `sort()` then `pop(0)` is the simplest correct priority queue. Tuples sort by `ready`, then `seq`.

```python
while q:
    q.sort()
    ready, _, sid, attempt = q.pop(0)
    start = max(loop.now(), ready)
    if last_start is not None:
        start = max(start, last_start + cfg["interval"])
    if start > loop.now():
        yield start - loop.now()
    last_start = loop.now()
```

The `if start > loop.now()` guard skips a zero-length sleep. `yield 0` would still work, but it would hand the turn to other tasks at the same time and could reorder the attempt log.

**Step 3: send and classify.** Catch `BadRequestError` in its own `except` before `ToolError`, so permanent errors never reach the retry branch.

```python
    try:
        yield from send(sid, name)
        delivered[sid] = loop.now()
    except BadRequestError:
        failed[sid] = "rejected"
    except ToolError:
        if attempt >= cfg["max_attempts"]:
            failed[sid] = "exhausted"
        else:
            q.append((loop.now() + cfg["retry_delay"] * 2 ** (attempt - 1), next_seq[0], sid, attempt + 1))
            next_seq[0] += 1
```

`loop.now()` after `send` is the finish time, which is what both `delivered` and the backoff use. Using `last_start` as the base instead moves every retry earlier by one latency: Example 3's second attempt starts at 0.75 instead of 0.875.

**Step 4: spawn and run.**

```python
for name in sorted(queues):
    loop.spawn(worker(name), "channel:" + name)
loop.run()
return {"delivered": delivered, "failed": failed}
```

Forget `loop.run()` and nothing happens: the workers are spawned but never stepped, and every case comes back with empty `delivered` and `failed`.

## 8. Full solution

```python
# the two failure kinds send can raise: permanent and transient
from gc_runtime import BadRequestError, ToolError


# notify every subscriber, one rate-limited worker per channel
def fanout(loop, subscribers, channels, send):
    delivered, failed = {}, {}  # the two result maps the judge reads
    queues = {}  # channel -> list of (ready_time, seq, subscriber_id, attempt)
    for i, s in enumerate(subscribers):  # the index is the tie-break seq
        queues.setdefault(s["channel"], []).append((0.0, i, s["id"], 1))  # everyone is ready at t=0
    next_seq = [len(subscribers)]  # shared retry counter; a list so closures can bump it

    # the single sender for one channel
    def worker(name):
        cfg = channels[name]  # this channel's interval, attempt cap and base backoff
        q = queues[name]  # this channel's own queue
        last_start = None  # no attempt has started yet on this channel
        while q:  # until every subscriber is delivered or given up on
            q.sort()  # smallest (ready_time, seq) first
            ready, _, sid, attempt = q.pop(0)  # take the next item
            start = max(loop.now(), ready)  # can't start before now or before it is ready
            if last_start is not None:  # the rate limit only applies after the first attempt
                start = max(start, last_start + cfg["interval"])  # space starts by the interval
            if start > loop.now():  # only sleep when we actually have to wait
                yield start - loop.now()  # advance virtual time to the allowed start
            last_start = loop.now()  # the limit counts starts, so record it now
            try:  # classify how this attempt ends
                yield from send(sid, name)  # takes the channel's latency, may raise
                delivered[sid] = loop.now()  # delivered at the finish time
            except BadRequestError:  # permanent: retrying would fail the same way
                failed[sid] = "rejected"  # give up at once
            except ToolError:  # transient: maybe retry
                if attempt >= cfg["max_attempts"]:  # this was the last allowed attempt
                    failed[sid] = "exhausted"  # out of attempts
                else:  # requeue instead of sleeping, so others on the channel go first
                    # ready after an exponential backoff measured from the finish
                    q.append((loop.now() + cfg["retry_delay"] * 2 ** (attempt - 1), next_seq[0], sid, attempt + 1))
                    next_seq[0] += 1  # retries are numbered in the order they are queued

    for name in sorted(queues):  # one worker per channel, in sorted name order
        loop.spawn(worker(name), "channel:" + name)  # channels run independently
    loop.run()  # drive every worker to completion in virtual time
    return {"delivered": delivered, "failed": failed}  # the shape the judge expects
```

## 9. How the test cases map to the code

| test case | expected (from the judge) | what it checks |
|---|---|---|
| Example 1 | email first at 0; ana 0.25, ops 0.5, ben 1.25 | one worker per channel, spawned in sorted order; interval between starts |
| Example 2 | ben 1.25, cho 2.25, ana's retry starts at 3.0 | the failed subscriber is requeued, not slept on |
| Example 3 | hook-billing rejected after 1 attempt; hook-crm exhausted after 4, `t = 4.25` | permanent vs transient errors; backoff 0.5, 1.0, 2.0 from the finish |
| single subscriber | delivered at 0.5 | no wait before the first attempt |
| retry interleaves with queue | u00 delivered 3.25 after retries at 2.0 and 3.125; u05 rejected | retries rejoin the queue by `(ready_time, seq)` |
| three channels with failures | ana exhausted at `t = 7.5` while webhook is done by 2.125 | channels never wait on each other |
| zero interval | c 0.375, a 0.5, b exhausted | `interval = 0` and `retry_delay = 0` still work |
| slow channel, interval shorter than latency | x2 2, x3 3, x1 4 | with latency 1.0 > interval 0.25, the worker's own busy time sets the pace |
| two channels, both retrying | w2 delivered 1, w1 4 | head-of-line isolation on two channels at once |
| many subscribers | 19 delivered, 11 failed | everything at once across 30 subscribers |

## 10. Complexity

With `n` subscribers and up to `A = max_attempts` attempts each, a channel's worker runs at most `n·A` iterations. Each re-sorts the queue, so the total is O(n·A · n log n) here. That is fine for 40 items. A `heapq` makes each pick O(log n), for O(n·A log n) in all. Memory is O(n).

The wall time a channel needs is set by its rate limit: at least `(attempts on that channel − 1) × interval` plus one latency, and never less than the sum of latencies, because one worker sends one message at a time. In "slow channel, interval shorter than latency" the 0.25 s interval is irrelevant: four 1-second sends take 4 seconds. In production you'd allow several sends in flight per channel (a token bucket or a concurrency cap) rather than one at a time.

## 11. If you got Wrong Answer

- **Everyone behind a failing subscriber is delivered late** (Example 2: ben at 3.5 instead of 1.25). You sleep the backoff inside the worker: `wrong_head_of_line_retry.py`.
- **Every gap is one latency too long** (Example 1: ben at 1.5 instead of 1.25). You set `last_start` after `send` returns: `wrong_interval_from_finish.py`.
- **A rejected subscriber shows up in `delivered`** (Example 3: `hook-billing`). You catch `BadRequestError` together with `ToolError` and retry it: `wrong_retries_permanent_errors.py`.
- **One channel's sends are delayed by another's** (Example 1: ana at 1.25 instead of 0.25). One `last_start` is shared across channels: `wrong_shared_limiter_across_channels.py`.
- **Retries are late, such as ana delivered at 4.5 instead of 3.25 in Example 2.** Your backoff exponent is off by one: `2 ** attempt` instead of `2 ** (attempt - 1)`.
- **Retries are early by one latency** (Example 3: the second attempt at 0.75 instead of 0.875). You add the backoff to the start time instead of the finish.
- **An exhausted subscriber is delivered** (Example 3: `hook-crm`). You check `attempt > max_attempts`, which allows one extra attempt.
- **The first attempt is on `slack`, not `email`.** You spawn workers in dict order instead of `sorted(queues)`.

## 12. Follow-ups an interviewer might ask

- *How would you allow more than one send in flight per channel?* Replace `last_start` with a token bucket (problem 123, token-bucket-rate-limiter) and run `k` workers per channel that share the bucket and the queue. The queue order stays `(ready_time, seq)`.
- *Slack returns 429 with `Retry-After`. Where does that go?* Treat it as transient, but use the server's delay as the ready time instead of your own backoff, and push the channel's next allowed start out too. Adding jitter avoids synchronized retries when many workers back off together (problem 124, retry-with-backoff).
- *What happens to subscribers that end up `failed`?* Write them to a dead-letter queue with the reason and the attempt log, and surface them in the run's audit trail so a user can see why they were never notified.
- *A burst of 100,000 notifications arrives. What changes?* The queues move to Kafka, SQS or Redis Streams, partitioned by channel (and often by workspace). Put a bound on them so the burst can't exhaust memory (problem 174, bounded-queue-backpressure).
- *How do you avoid notifying someone twice after a crash?* Make each send idempotent with a key like `run_id:subscriber_id`, so a replayed send is recognized and skipped by the provider or by your own dedupe table (problem 180, api-idempotent-create).
