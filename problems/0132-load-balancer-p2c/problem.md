One replica of your inference service landed on a degraded GPU node and runs at a quarter of normal speed. Round-robin keeps sending it a quarter of the traffic, and your p99 is on fire. Simulate the balancing policies so that you can show the team what least-outstanding-requests and **power of two choices** (P2C) would have done.

`simulate_lb(requests, replicas, policy, pick2)` takes

- `requests`: `[{"id", "arrival", "work"}]` sorted by `arrival` (ties keep input order). Times are in seconds.
- `replicas`: `[{"name", "speed", "slots"}]`. A replica runs up to `slots` requests at once (its batch). A request takes `work / speed` seconds once it starts, and requests beyond `slots` wait in that replica's FIFO queue.
- `policy`: `"round_robin"`, `"least_outstanding"` or `"p2c"`.
- `pick2()`: returns a pair of distinct replica indices `(a, b)`, standing in for P2C's random sample.

The balancer does **not** know the speeds. It only sees each replica's **outstanding** count: requests in service plus requests queued there.

| policy | choice for the k-th request (k from 0) |
|---|---|
| `round_robin` | replica `k % n` |
| `least_outstanding` | the fewest outstanding; ties go to the lowest index |
| `p2c` | call `pick2()` once to get `(a, b)` and take the one with fewer outstanding; a tie goes to `a` |

Don't call `pick2()` under any other policy.

**Event order.** Process events in time order. At equal times, process every **completion** before any **arrival**. When a request completes, its replica immediately starts the head of its queue, if there is one, at that same time. An arriving request is assigned at its arrival time: it starts right away if the replica has a free slot, and otherwise joins the queue.

Return

```
{"assignment": [replica index per request, input order],
 "latency": [finish - arrival per request, input order],
 "p50": float, "p99": float,
 "max_outstanding": [highest outstanding count each replica reached]}
```

Percentiles are nearest-rank: sort the latencies and take index `ceil(q * n) - 1`. The judge runs your function once for each policy in the case and also counts your `pick2()` calls.

**Constraints**

- `2 <= len(replicas) <= 16`, `1 <= len(requests) <= 2000`, `speed > 0`, `slots >= 1`
- Don't import `random`; P2C's randomness comes only from `pick2()`
