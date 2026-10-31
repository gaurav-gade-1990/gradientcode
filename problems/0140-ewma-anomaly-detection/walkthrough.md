## 1. What the problem is really asking

Strip away the latency story and this is a **running z-score with a gate on what it learns from**:

> for each new value: if you're still warming up, just learn it → otherwise, measure how many (floored) standard deviations it is from the running mean → flag it if that's more than `k` → learn from it only if it wasn't flagged.

The running mean and variance are exponentially weighted (EWMA), so recent minutes count more than old ones and the state is two floats, whatever the length of the series. The formulas are given. What the problem tests is the **order of operations** and three small rules around them: score before learning, never learn from an anomaly, and floor the standard deviation.

The judge's driver records, for every point, the returned `z` (or `None`), the anomaly flag, **and your `self.mean` and `self.var` right after the call**. So the baseline itself is graded at every index, not just the flags. A detector that flags the right points but updates its baseline on the wrong ones still fails.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `alpha` | EWMA weight of the newest point, `0 < alpha < 1` | the step size in the mean and variance update |
| `k` | z-score threshold | anomaly when `abs(z) > k`, strictly |
| `warmup` | number of leading points that are learned but never scored, **including index 0** | scoring starts at index `warmup` |
| `min_std` | the smallest standard deviation you'll divide by | `max(sqrt(var), min_std)` |
| `update(value)` | called once per point, in order | returns `{"z": float or None, "anomaly": bool}` |
| `self.mean`, `self.var` | the baseline | read by the judge after every call |

The update rule (Finch, 2009), with `d = x - mean` computed **before** the mean changes:

```
mean <- mean + alpha * d
var  <- (1 - alpha) * (var + alpha * d * d)
```

Three details are easy to miss:

- **Index 0 is special.** It sets `mean = x` and `var = 0.0`. It doesn't run the update formula, since there is no previous mean to take a difference from.
- **`warmup` counts index 0.** With `warmup = 3`, indices 0, 1 and 2 are learned without scoring, and index 3 is the first scored point. With `warmup = 1`, scoring starts at index 1.
- **`d` uses the old mean in both lines.** Compute `d` once, then update the mean, then the variance. If you recompute `x - self.mean` after the mean has moved, the variance comes out wrong.

## 3. Trace Example 1 by hand

`series = [82, 84, 83, 85, 84, 140, 83]`, `alpha = 0.3`, `k = 3`, `warmup = 3`, `min_std = 1`.

| i | x | phase | d | z | anomaly | mean after | var after |
|---|---|---|---|---|---|---|---|
| 0 | 82 | first point | - | None | False | 82 | 0 |
| 1 | 84 | warmup, learn | 2 | None | False | 82.6 | 0.7·(0 + 0.3·4) = 0.84 |
| 2 | 83 | warmup, learn | 0.4 | None | False | 82.72 | 0.7·(0.84 + 0.3·0.16) = 0.6216 |
| 3 | 85 | score, then learn | 2.28 | 2.28 / max(0.788, **1**) = **2.28** | False | 83.404 | 1.52678 |
| 4 | 84 | score, then learn | 0.596 | 0.596 / 1.2356 = 0.4823 | False | 83.5828 | 1.14334 |
| 5 | 140 | score only | - | 56.4172 / 1.06927 = **52.7622** | **True** | 83.5828 | 1.14334 |
| 6 | 83 | score, then learn | -0.5828 | -0.545 | False | 83.408 | 0.871669 |

Three things to notice:

- At index 3, `sqrt(0.6216) = 0.788` is below `min_std = 1`, so the floor is what you divide by.
- At index 5, `mean` and `var` are **unchanged**. The judge sees `mean[5] == mean[4]`.
- Index 6 is scored against the clean baseline, so 83 ms looks normal (z = -0.545).

The result is `anomalies = [5]`.

### The tricky hidden case: "point right after spike"

`[60, 61, 59, 60, 62, 61, 60, 59, 95, 66, 61]` with `alpha = 0.4`, `k = 3`, `warmup = 6`, `min_std = 1`. Index 8 (95 ms) scores z = 35.1 and is flagged. The baseline stays at mean 59.9044, var 0.930219. Index 9 (66 ms) is then scored against that tight baseline: `sqrt(0.930)` is under the floor, so z = (66 - 59.9044) / 1 = **6.0956**, and it is flagged too. Only index 10 (61 ms) is back to normal.

So the expected anomalies are `[8, 9]`. If the spike had been learned, the mean would have jumped to 73.94 and the variance to 296, and 66 ms would look ordinary (z = -0.46). The recovery minute would hide.

## 4. Key idea: score against the baseline *before* the point

If you learn first and score after, the point is already part of the mean and variance it's compared with. A big spike inflates the variance in the same step, so its own z-score shrinks. In Example 1, learning first makes index 5's z-score **1.53** instead of 52.76, and the detector sees nothing at all. The rule is: the baseline is a description of the past, and the new point is judged against the past.

## 5. Key idea: anomalies are reported, never learned

A flagged point leaves `mean` and `var` exactly as they were. Otherwise an incident teaches the detector that incidents are normal. In "level shift stays anomalous", latency moves from about 80 ms to about 140 ms at index 60. Because the detector never learns the new level, every point from 60 to 99 is flagged. If anomalies were learned, only index 60 would be flagged, and the detector would go quiet after one minute of a real regression.

This has a cost: a *permanent* change (a slower new model) is flagged forever. The problem accepts that on purpose, and the follow-ups discuss how real detectors re-baseline.

The flip side is "outlier inside warmup is learned". A 300 ms point at index 2 falls inside the warmup, so it is learned without scoring. It inflates the variance to 11051.7, and the 250 ms point at index 7 then scores only z = 2.745, so it isn't flagged. That's the expected answer: warmup points are trusted by definition.

## 6. Key idea: a floor, not an epsilon

A cached endpoint can be perfectly flat, so `var = 0`. Dividing by `sqrt(var) + 1e-9` avoids the crash but turns a 0.5 ms wobble into z = 5·10⁸. `max(sqrt(var), min_std)` says "differences smaller than this many milliseconds are noise". In Example 2 the floor is 2 ms, so 50.5 ms scores z = 0.25, while 59 ms scores 9 / 2 = 4.5 and crosses `k = 4`.

## 7. Plan before you code

```
__init__: store alpha, k, warmup, min_std; mean = var = None; seen = 0
_learn(x): d = x - mean; mean += alpha * d; var = (1 - alpha) * (var + alpha * d * d)
update(x):
    i = seen; seen += 1
    if i == 0: mean = x; var = 0; return no score
    if i < warmup: learn; return no score
    z = (x - mean) / max(sqrt(var), min_std)
    anomaly = |z| > k
    if not anomaly: learn
    return z and anomaly
```

| index | scored? | learned? |
|---|---|---|
| 0 | no | sets mean = x, var = 0 |
| 1 .. warmup-1 | no | yes |
| ≥ warmup, `abs(z) <= k` | yes | yes |
| ≥ warmup, `abs(z) > k` | yes | no |

## 8. Build it one piece at a time

**Step 1: state.** Keep a counter of points seen, because the phase depends on the index. Start `mean` and `var` as `None`. The first point fills them.

```python
def __init__(self, alpha, k, warmup, min_std):
    self.alpha, self.k, self.warmup, self.min_std = alpha, k, warmup, min_std
    self.mean = None
    self.var = None
    self.seen = 0
```

**Step 2: the learning step.** Put it in its own method, because it's called from two places (warmup and normal points). Compute `d` once, before the mean moves.

```python
def _learn(self, x):
    d = x - self.mean
    self.mean += self.alpha * d
    self.var = (1 - self.alpha) * (self.var + self.alpha * d * d)
```

**Step 3: the phases.** Read the index, then increment the counter, so `i` is this point's 0-based index. Handle index 0 and warmup with early returns.

```python
x = float(value)
i = self.seen
self.seen += 1
if i == 0:
    self.mean, self.var = x, 0.0
    return {"z": None, "anomaly": False}
if i < self.warmup:
    self._learn(x)
    return {"z": None, "anomaly": False}
```

**Step 4: score, then gate the learning.**

```python
z = (x - self.mean) / max(math.sqrt(self.var), self.min_std)
anomaly = abs(z) > self.k
if not anomaly:
    self._learn(x)
return {"z": z, "anomaly": anomaly}
```

`abs` matters: a 40 ms reading on a 210 ms endpoint ("drop is anomalous too") has z = -69 and must be flagged.

## 9. Full solution

```python
import math  # for the square root of the variance


# Streaming EWMA anomaly detector over a latency series.
class EwmaDetector:
    # Store the settings; the baseline is filled in by the first point.
    def __init__(self, alpha, k, warmup, min_std):
        self.alpha, self.k, self.warmup, self.min_std = alpha, k, warmup, min_std  # fixed for the whole series
        self.mean = None  # no baseline until the first point arrives
        self.var = None  # likewise for the variance
        self.seen = 0  # number of points processed, which decides the phase

    # Fold one point into the EWMA mean and variance (Finch's incremental form).
    def _learn(self, x):
        d = x - self.mean  # distance from the OLD mean, used by both updates
        self.mean += self.alpha * d  # move the mean a fraction alpha toward x
        self.var = (1 - self.alpha) * (self.var + self.alpha * d * d)  # decay old spread, add this point's

    # Process one value and report its score.
    def update(self, value):
        x = float(value)  # the judge may pass ints; keep the arithmetic in floats
        i = self.seen  # this point's 0-based index
        self.seen += 1  # count it before any early return
        # The first point defines the baseline; there's nothing to compare it to.
        if i == 0:
            self.mean, self.var = x, 0.0  # a single point has no spread
            return {"z": None, "anomaly": False}  # never scored
        # Warmup points are trusted: learn them, don't score them.
        if i < self.warmup:
            self._learn(x)  # build up a baseline worth scoring against
            return {"z": None, "anomaly": False}  # still warming up
        # Score against the baseline as it was before this point, with a floored std.
        z = (x - self.mean) / max(math.sqrt(self.var), self.min_std)
        anomaly = abs(z) > self.k  # spikes and drops both count; strict comparison
        # Only normal points may change the baseline.
        if not anomaly:
            self._learn(x)  # an anomaly is reported but never becomes the new normal
        return {"z": z, "anomaly": anomaly}  # the score and the verdict for this point
```

## 10. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | anomalies `[5]`, z[5] = 52.76, mean unchanged at index 5 | score before learning; anomalies don't update the baseline |
| Example 2 | anomalies `[6]`, z = 0.25 for the 0.5 ms wobble | the `min_std` floor on a flat series |
| steady traffic no anomalies | no anomalies | normal noise stays under `k = 4` |
| spikes do not poison the baseline | anomalies `[40, 41, 90]` | two spikes in a row are both caught; a drop at 90 too |
| level shift stays anomalous | 32, then every index from 60 to 99 | a never-learned shift is flagged forever; index 32 is a natural noise outlier (z = -3.78) |
| flat series with tiny wobble | no anomalies, z at most 1.99 | the floor of 0.5 ms absorbs a 1 ms bump |
| outlier inside warmup is learned | no anomalies | warmup points are learned unconditionally, even a 300 ms one |
| warmup 1 scores from index 1 | anomalies `[2]`, z = [None, 0.667, 43, -1, 1.5] | `warmup` counts index 0 |
| drop is anomalous too | anomalies `[7]`, z = -69.04 | `abs(z)`, not `z > k` |
| single point | z `[None]`, mean `[88]`, var `[0]` | index 0 alone |
| point right after spike | anomalies `[8, 9]` | the clean baseline exposes the elevated minute after a spike |

## 11. Complexity

Each `update` is O(1) time and the detector is O(1) memory: three floats and a counter. A 2,000-point series is trivial.

That constant footprint is the reason to use an EWMA in production. You might track one detector per (model, region, tenant, metric), which can be hundreds of thousands of series. A rolling-window z-score would need to store the window for each one, while an EWMA needs two numbers. `alpha` sets the memory: the effective window is about `2/alpha - 1` points, so `alpha = 0.1` behaves like a 19-minute window.

## 12. If you got Wrong Answer

Compare `mean` and `var` with the expected arrays and find the first index that differs:

- **In Example 1, index 5 is flagged but `mean[5]` is 100.508 and `var[5]` is 669.2.** You learn from anomalies. Skip `_learn` when the point is flagged. "point right after spike" then also loses index 9.
- **In Example 1, nothing is flagged and z[5] is 1.53.** You learn first and score after. Compute `z` before calling `_learn`.
- **In Example 1, z[1] is 2 and z[2] is 0.4 instead of None.** You score during warmup. With `warmup = 3`, indices 0 to 2 return `z = None`.
- **In Example 2, indices 4, 5 and 6 are all flagged, with z near 5·10⁸.** You used `sqrt(var) + epsilon`. Use `max(sqrt(var), min_std)`.
- **"drop is anomalous too" has no anomalies.** You compared `z > k`. Use `abs(z) > k`.
- **`var` is slightly off from index 1.** You recomputed `x - self.mean` after updating the mean. Compute `d` once.

## 13. Follow-ups an interviewer might ask

- *How do you handle a permanent level shift, like a new model that's always slower?* Re-baseline after N consecutive anomalies (reset `mean` to the recent level and widen `var`), or run a second, slower EWMA and alert on the gap between the fast and slow means.
- *How do you handle daily seasonality?* The morning ramp would be "anomalous" every day. Keep a baseline per hour-of-week, or subtract last week's value at the same minute and run the EWMA on the residual.
- *Why not just a static threshold?* Each model has its own normal: a reranker idles at 40 ms, a 70B chat model at 2 s. An EWMA learns each series' level and spread, so one `k` works everywhere.
- *How does this relate to SLO alerts?* This answers "something changed". A burn-rate alert answers "users are hurting" and is what should page (problem 139, slo-burn-rate-alerts). The p95 series fed in here comes from a streaming percentile estimator (problem 138, streaming-latency-percentiles).
- *What about distribution changes rather than single-point spikes?* Compare whole windows of values with a two-sample test (problem 136, ks-drift-detector).
