## Approach

A canary controller is a small state machine over analysis windows: two streak counters, a short-circuit abort, and a rule that refuses to judge thin data.

```python
for w in windows:
    if r_c > 0 and 10000 * e_c > abort_bp * r_c:            # on fire: don't wait
        decision = "rollback"
    elif r_c < min_requests or r_b < min_requests:          # too little data
        decision = "extend"                                  # streaks untouched
    else:
        fails = error_rate_worse + p99_worse
        ...update streaks, maybe promote or rollback...
    if decision in ("promote", "rollback"):
        break
```

Two details carry most of the weight.

- **Per-window judgment.** A cumulative ratio hides a regression that starts late: after an hour of clean traffic, a canary now failing 4.5% of requests still averages under the limit.
- **Integer thresholds.** `e_c/r_c - e_b/r_b > delta` in floats can flip at the boundary. Cross-multiplying gives `10000 * (e_c * r_b - e_b * r_c) > bp * r_c * r_b`, which is exact.

Nearest-rank p99 uses `k = ceil(0.99 n)` written as `(99 n + 99) // 100`, again to keep floats out of an index.

## Common mistakes

- **Mean latency.** If 3% of requests start timing out at 6x latency, the mean moves a little while p99 moves a lot, and p99 is what users and SLOs see.
- **No minimum sample size.** Right after the rollout starts, or overnight, a window has a handful of requests. One error is a "25% error rate", and you roll back a good build.
- **Non-consecutive streaks.** Counting total failures means two unrelated blips an hour apart kill the rollout. Consecutive streaks ask for sustained evidence.
- **Pooling windows.** See above. The late regression is exactly the case canaries exist to catch.
- **Not stopping.** If the analysis keeps running after a rollback, a later healthy window "promotes" a build that is already gone, or worse, re-deploys it.

## Production notes

- Argo Rollouts `AnalysisTemplate` (with `failureLimit`, `count` and `interval`), Flagger, and Spinnaker's Kayenta all implement this loop. Kayenta uses a Mann-Whitney test per metric instead of fixed thresholds, which pairs with `ab-test-significance`.
- Compare against a **baseline started at the same time** as the canary, not against the old fleet. A fresh pod has cold caches and a warming JIT, and comparing it against warm pods is a classic source of false latency regressions.
- For LLM builds, add quality metrics to the analysis: refusal rate, tool-call error rate, the online judge score, and tokens per response. An error rate of 0 with every answer doubling in length is still a regression (and a cost incident).
- Wire the rollback to the registry (`model-registry-stages`) so the alias flips back automatically, and page someone only when the abort rule fires.
