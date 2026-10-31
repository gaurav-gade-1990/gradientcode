## 1. What the problem is really asking

Under the story about a degraded GPU, this is a **discrete-event simulation** with two kinds of events (an arrival and a completion) and one routing decision per arrival. You keep a clock, a heap of future events, and per replica a count of busy slots, a FIFO queue and an **outstanding** counter. Each policy is a different function from "the outstanding counts right now" to "which replica gets this request".

The point of the exercise is that the balancer never sees `speed`. Least-outstanding and P2C still avoid a slow replica, because a slow replica holds its requests longer, so its counter stays high. You are simulating how well that indirect signal works.

The judge's driver calls your function once per policy listed in the case and records the whole return dict plus `pick2_calls`, the number of times you called `pick2()`. So every field is graded: the replica index per request, every latency, both percentiles and the peak outstanding count per replica. A wrong tie rule or a wrong event order usually shows up in `max_outstanding` even when every latency is right.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `requests` | `[{"id", "arrival", "work"}]`, sorted by arrival | one arrival event each; service time is `work / speed` |
| `replicas` | `[{"name", "speed", "slots"}]` | `slots` concurrent requests per replica; the rest queue FIFO |
| `policy` | `"round_robin"`, `"least_outstanding"` or `"p2c"` | picks the routing rule |
| `pick2()` | returns `(a, b)`, two distinct indices | call it once per request, only under `p2c` |
| return value | `assignment`, `latency`, `p50`, `p99`, `max_outstanding` | all in input order; percentiles are nearest-rank |

Three details are easy to miss:

- **Outstanding means in service plus queued.** A replica with every slot busy and an empty queue is not idle. The counter goes up on assignment and down on completion, nowhere else.
- **Completions before arrivals at the same time.** If a request finishes at `t=1.0` and another arrives at `t=1.0`, the finished slot is already free when the arrival is routed. This changes both the routing and `max_outstanding`.
- **The driver's `pick2()` is a recording.** It raises `AssertionError` if you call it more times than there are requests, and `pick2_calls` is compared. Calling it under `least_outstanding` "just to have the pair" fails the case.

## 3. Trace Example 2 by hand

Four replicas, all with one slot. `gpu-d-degraded` (index 3) runs at speed 0.25, so a request with `work=1` takes 4 s there and 1 s elsewhere. Requests arrive every 0.25 s. The recorded pairs are `[3,0], [0,1], [2,3], [3,1], [3,2], [0,3]`.

| t | event | pair `(a, b)` | outstanding a vs b | choice | starts | finishes |
|---|---|---|---|---|---|---|
| 0.00 | r000 arrives | (3, 0) | 0 vs 0, tie | 3 | 0.00 | 4.00 |
| 0.25 | r001 arrives | (0, 1) | 0 vs 0, tie | 0 | 0.25 | 1.25 |
| 0.50 | r002 arrives | (2, 3) | 0 vs 1 | 2 | 0.50 | 1.50 |
| 0.75 | r003 arrives | (3, 1) | 1 vs 0 | 1 | 0.75 | 1.75 |
| 1.00 | r004 arrives | (3, 2) | 1 vs 1, tie | 3 | queued | 8.00 |
| 1.25 | r001 completes, then r005 arrives | (0, 3) | 0 vs 2 | 0 | 1.25 | 2.25 |

r004 queues behind r000 on the slow replica, starts at 4.0 when r000 completes and finishes at 8.0, so its latency is 7. The reference output is:

```python
{'assignment': [3, 0, 2, 1, 3, 0], 'latency': [4, 1, 1, 1, 7, 1],
 'p50': 1, 'p99': 7, 'max_outstanding': [1, 1, 1, 2], 'pick2_calls': 6}
```

Look at the last row. At `t=1.25` there are two events, r001's completion and r005's arrival. Processing the completion first drops replica 0 to 0 outstanding before r005 compares 0 against replica 3's 2.

**Example 3 is the tie rule at its smallest.** Two one-slot replicas. `a` (work 1) and `b` (work 2) arrive at 0 and go to r0 and r1. `c` arrives at exactly `t=1.0`, the instant `a` finishes. With completions first, r0 shows 0 outstanding and r1 shows 1, so `c` goes to r0 and starts at once. Expected: `assignment [0, 1, 0]`, `max_outstanding [1, 1]`. If you process the arrival first, `c` still lands on r0 (a 1-1 tie goes to the lowest index), but for an instant r0 holds 2, and you output `max_outstanding [2, 1]`. Same latencies, Wrong Answer.

## 4. Key idea: encode "completions first" in the heap key

You don't need a special case for simultaneous events. Push every event as a tuple:

```python
(time, kind, seq, payload)    # kind 0 = completion, 1 = arrival
```

Python compares tuples left to right, so at equal `time` the smaller `kind` pops first: every completion before any arrival. `seq` is a counter that breaks the remaining ties in push order, which keeps arrivals at the same instant in input order (the "burst at one instant" case has ten of them at `t=0`). It also stops Python from ever comparing two payloads.

## 5. Key idea: the tie rule is part of the policy

The two counting policies break ties differently, and the tests pin both.

- `least_outstanding`: the fewest outstanding, ties to the **lowest index**. `min(range(n), key=lambda j: (outstanding[j], j))` says that in one line.
- `p2c`: ties to **`a`, the first sample**, whatever its index. Write `b if outstanding[b] < outstanding[a] else a`. The strict `<` is the tie rule.

Taking the lower index of the pair looks equivalent but isn't. In "p2c ties take the first draw" every request arrives 10 s apart, so every comparison is a 0-0 tie. The expected assignment is the first element of each pair, `[2, 1, 3, 0, 1]`. Lowest-index gives `[1, 0, 2, 0, 1]`.

## 6. Plan before you code

```
outstanding, busy, peak = [0]*n each; queues = one deque per replica
push an arrival event per request; k = 0
while events:
    pop (now, kind, _, payload)
    completion (rep, i):
        finish[i] = now; busy[rep] -= 1; outstanding[rep] -= 1
        if queues[rep]: start the head at now
    arrival i:
        rep = policy choice (uses k, or a scan, or pick2)
        k += 1; assignment[i] = rep
        outstanding[rep] += 1; peak[rep] = max(peak[rep], outstanding[rep])
        if busy[rep] < slots: start i at now   else: queue it
latency = finish - arrival; sort; nearest-rank p50 and p99
```

`start(rep, i, now)` bumps `busy[rep]` and pushes a completion at `now + work / speed`.

## 7. Build it one piece at a time

**Step 1: state and the event heap.** All arrivals are known up front, so push them all and `heapify` once.

```python
    n = len(replicas)
    outstanding, busy, peak = [0] * n, [0] * n, [0] * n
    queues = [deque() for _ in range(n)]
    finish = [None] * len(requests)
    assignment = [None] * len(requests)
    events = [(r["arrival"], 1, i, i) for i, r in enumerate(requests)]
    heapq.heapify(events)
    seq = len(requests)
```

**Step 2: starting a request.** Service time is `work / speed`, counted from when it *starts*, not from when it arrived. A queued request's wait is the gap between the two, and it shows up in its latency.

```python
    def start(rep, i, now):
        nonlocal seq
        busy[rep] += 1
        heapq.heappush(events, (now + requests[i]["work"] / replicas[rep]["speed"], 0, seq, (rep, i)))
        seq += 1
```

**Step 3: completions.** Decrement `outstanding` here, on every completion. If you forget, the counter turns into "requests ever assigned", and least-outstanding degenerates into round robin: in Example 1 it would send r003 to the slow replica.

```python
        if kind == 0:
            rep, i = payload
            finish[i] = now
            busy[rep] -= 1
            outstanding[rep] -= 1
            if queues[rep]:
                start(rep, queues[rep].popleft(), now)
            continue
```

**Step 4: arrivals and the three policies.** `k` counts requests routed so far, so round robin is `k % n`. `pick2()` sits inside the `p2c` branch only.

```python
        i = payload
        if policy == "round_robin":
            rep = k % n
        elif policy == "least_outstanding":
            rep = min(range(n), key=lambda j: (outstanding[j], j))
        else:
            a, b = pick2()
            rep = b if outstanding[b] < outstanding[a] else a
        k += 1
        assignment[i] = rep
        outstanding[rep] += 1
        peak[rep] = max(peak[rep], outstanding[rep])
        if busy[rep] < replicas[rep]["slots"]:
            start(rep, i, now)
        else:
            queues[rep].append(i)
```

**Step 5: nearest-rank percentiles.** Rank `ceil(q·n)` is 1-based, so the index is `ceil(q·n) - 1`. With 40 latencies, p50 is index 19, the 20th value. `int(0.5 * 40) = 20` reads one past it.

```python
    def pct(q):
        return srt[max(0, math.ceil(q * len(srt)) - 1)]
```

## 8. Full solution

```python
import heapq                                   # the event queue: always pop the earliest event
import math                                    # ceil for nearest-rank percentiles
from collections import deque                  # O(1) FIFO queue per replica


def simulate_lb(requests, replicas, policy, pick2):    # one simulation for one policy
    n = len(replicas)                          # number of replicas, used by round robin and the scan
    outstanding = [0] * n                      # in service + queued: the only load signal the balancer sees
    busy = [0] * n                             # slots in use, compared with each replica's slots
    queues = [deque() for _ in range(n)]       # requests waiting for a free slot, in arrival order
    peak = [0] * n                             # highest outstanding count each replica reached
    finish = [None] * len(requests)            # completion time per request, filled in by completions
    assignment = [None] * len(requests)        # chosen replica per request, in input order
    # heap entries are (time, kind, seq, payload); kind 0 = completion sorts before 1 = arrival
    events = []
    seq = 0                                    # push counter: keeps same-time events in push order
    for i, r in enumerate(requests):           # every arrival is known up front
        events.append((r["arrival"], 1, seq, i))   # arrival event carries the request index
        seq += 1                               # next push gets a later tie-break number
    heapq.heapify(events)                      # one O(R) build instead of R pushes

    def start(rep, i, now):                    # put request i into service on replica rep at time now
        nonlocal seq                           # the counter lives in the enclosing function
        busy[rep] += 1                         # it takes one slot until it completes
        # service time is work / speed, counted from when it starts, not from arrival
        heapq.heappush(events, (now + requests[i]["work"] / replicas[rep]["speed"], 0, seq, (rep, i)))
        seq += 1                               # keep tie-break numbers unique

    k = 0                                      # requests routed so far, drives round robin
    while events:                              # run until every request has completed
        now, kind, _, payload = heapq.heappop(events)  # the earliest event; completions win ties
        if kind == 0:                          # a completion frees a slot and lowers the load
            rep, i = payload                   # which replica, which request
            finish[i] = now                    # its latency is measured to this instant
            busy[rep] -= 1                     # the slot is free again
            outstanding[rep] -= 1              # without this, the count becomes "ever assigned"
            if queues[rep]:                    # someone is waiting on this replica
                start(rep, queues[rep].popleft(), now)  # the FIFO head starts at the same instant
            continue                           # completions route nothing, go to the next event
        i = payload                            # an arrival: route request i
        if policy == "round_robin":            # ignores load entirely
            rep = k % n                        # the k-th request goes to replica k mod n
        elif policy == "least_outstanding":    # scans every replica
            rep = min(range(n), key=lambda j: (outstanding[j], j))  # fewest outstanding, ties to lowest index
        else:                                  # p2c: sample two, keep the less loaded
            a, b = pick2()                     # exactly one draw per request, and only under p2c
            rep = b if outstanding[b] < outstanding[a] else a   # strict <, so a tie keeps the first sample
        k += 1                                 # one more request routed
        assignment[i] = rep                    # record the decision for the judge
        outstanding[rep] += 1                  # it counts as load from the moment it is assigned
        peak[rep] = max(peak[rep], outstanding[rep])   # track the worst moment for this replica
        if busy[rep] < replicas[rep]["slots"]: # a free slot: no waiting
            start(rep, i, now)                 # starts at its arrival time
        else:                                  # every slot busy
            queues[rep].append(i)              # wait behind earlier requests on this replica

    latency = [finish[i] - r["arrival"] for i, r in enumerate(requests)]  # queue wait + service time
    srt = sorted(latency)                      # nearest rank works on the sorted list

    def pct(q):                                # nearest-rank percentile
        return srt[max(0, math.ceil(q * len(srt)) - 1)]   # rank ceil(q*n) is 1-based, so subtract 1

    # every field is graded, all lists in input order
    return {"assignment": assignment, "latency": latency, "p50": pct(0.50), "p99": pct(0.99), "max_outstanding": peak}
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | round robin p99 6, least outstanding p99 1 and never uses gpu-d | round robin is blind to speed; least outstanding adapts through the counter |
| Example 2 | `[3, 0, 2, 1, 3, 0]`, r004 latency 7 | P2C's first-sample tie rule and its blind spot: equal counts hide a slow replica |
| Example 3 | `[0, 1, 0]`, `max_outstanding [1, 1]` | completions before arrivals at the same instant |
| round robin piles onto a slow replica | round robin p99 29.2 and gpu-d peaks at 8; least outstanding p99 4 | the queue on a slow replica grows without bound under round robin |
| batched replicas with queueing | least outstanding p99 15.8, round robin 21.6 | `slots = 2`: `busy` vs `slots` and FIFO queues per replica |
| simultaneous completions and arrivals | least outstanding: every latency 2, gpu-d never used | completions land exactly on arrival times, over and over |
| burst at one instant | ten arrivals at `t=0`; round robin and least outstanding agree | `seq` keeps same-time arrivals in input order |
| p2c ties take the first draw | `[2, 1, 3, 0, 1]` | ties go to `a`, not to the lower index |
| fleet under load | 600 requests on 8 replicas, all three policies | everything at scale, including p99 at `n = 600` |
| small p99 sample | round robin p50 3, p99 8 on 7 latencies | nearest rank on a tiny sample |

## 10. Complexity

Each request produces one arrival and one completion, so there are `2R` heap operations at O(log R) each. Least-outstanding scans all `n` replicas per arrival, so that policy is O(R·n + R log R); P2C and round robin are O(1) per decision. Memory is O(R + n).

At scale that difference is the whole argument for P2C. A full scan needs one up-to-date view of every replica's load. Many balancer instances can't all have one without coordinating, and when they share a stale view they all pick the same "least loaded" replica at once and herd onto it. P2C needs only two fresh numbers per decision, and the randomness spreads the herd.

## 11. If you got Wrong Answer

Compare `max_outstanding` first; it is the field that exposes most bugs.

- **`max_outstanding` is one higher than expected, but latencies match** (Example 3 shows `[2, 1]`). You process arrivals before completions at the same time. Put the completion kind first in the heap tuple.
- **Least outstanding sends work to the slow replica as if it were round robin** (Example 1 gives assignment `[0, 1, 2, 3, 0, 1, 2, 3]` and `max_outstanding [2, 2, 2, 2]`). You never decrement `outstanding` on completion.
- **Least outstanding piles everything onto one replica** (Example 3 gives `[0, 0, 0]`). You count only the queue, so a replica whose slots are full looks empty. Count in-service requests too.
- **"p2c ties take the first draw" gives `[1, 0, 2, 0, 1]`.** You break P2C ties by index. Keep `a` unless `b` is strictly less loaded.
- **Only `p50` is off, and only on some cases** (least outstanding on "round robin piles onto a slow replica" gives 1.7 instead of 1.6). Your percentile index is `int(q * n)`. It differs from `ceil(q * n) - 1` exactly when `q * n` is a whole number, as `0.5 * 40` is.
- **`AssertionError: pick2() called more times...` or `pick2_calls` is non-zero for round robin.** You call `pick2()` outside the `p2c` branch.

## 12. Follow-ups an interviewer might ask

- *How do you make P2C see that a replica is slow, not just busy?* Weight the count by observed latency. Finagle and linkerd's peak-EWMA multiplies outstanding by a decayed latency estimate. The EWMA mechanics are in problem 140 (ewma-anomaly-detection).
- *Why not always use a full least-outstanding scan?* It costs O(n) per request, and across many balancer instances it needs shared, fresh state. Stale shared state makes every instance pick the same replica (herding). Two random choices avoid that, and Mitzenmacher showed they cut the maximum load exponentially compared with one random choice.
- *For LLM serving, is outstanding count the right signal?* Not quite: a 10-token request and a 4,000-token generation count the same. Route on model-server metrics such as queue depth and KV-cache utilization (the batching simulator in problem 129, continuous-batching-scheduler, shows where they come from), or on prefix-cache affinity with a load cap.
- *The slow replica is still getting some traffic. What else do you need?* Outlier ejection or a per-host circuit breaker (problem 125) to take it out of rotation, then autoscaling on queue depth (problem 133, autoscaler-policy) to replace the lost capacity.
- *How would you report percentiles at production volume?* You can't sort every latency. Use a streaming sketch or histogram, as in problem 138 (streaming-latency-percentiles).
