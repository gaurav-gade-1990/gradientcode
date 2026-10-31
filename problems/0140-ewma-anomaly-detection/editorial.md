## Approach

A static "page if p95 > 300 ms" threshold is wrong for every model you deploy: a reranker idles at 40 ms, a 70B chat model at 2 s. An EWMA learns each series' own level and spread and asks how many standard deviations the new minute is from them.

Three rules make it work in production:

1. **Score before you learn.** Compare `x` against the baseline as it was before `x`. If you update first, the spike pulls the mean toward itself and its own z-score shrinks.
2. **Don't learn from anomalies.** A flagged point is reported and then ignored by the baseline. Otherwise a ten-minute incident drags the mean up and the detector goes quiet halfway through.
3. **Floor the standard deviation.** A cached endpoint can be perfectly flat, so `var = 0` and any 0.1 ms wobble is z = infinity. `max(std, min_std)` says "differences smaller than this are noise".

```python
def update(self, value):
    x, i = float(value), self.seen
    self.seen += 1
    if i == 0:
        self.mean, self.var = x, 0.0
        return {"z": None, "anomaly": False}
    if i < self.warmup:
        self._learn(x)
        return {"z": None, "anomaly": False}
    z = (x - self.mean) / max(math.sqrt(self.var), self.min_std)
    anomaly = abs(z) > self.k
    if not anomaly:
        self._learn(x)        # d = x - mean; mean += a*d; var = (1-a)*(var + a*d*d)
    return {"z": z, "anomaly": anomaly}
```

The incremental update keeps O(1) state per series, which matters when you track every (model, region, tenant) triple.

## Common mistakes

- **Anomalies update the baseline.** The incident becomes the new normal within a few minutes.
- **An epsilon instead of a floor.** `std + 1e-9` avoids the division error but still turns a 0.3 ms wobble on a flat series into z of hundreds of millions.
- **Scoring after updating.** The spike is already part of the mean it is compared with, so big spikes look smaller and borderline ones disappear.
- **Scoring during warmup.** With two points the variance is meaningless and the first real minute after a deploy pages.

## Production notes

- The flip side of "don't learn from anomalies" is a level shift that never ends: after a model upgrade the new latency is flagged forever (see the level-shift case). Real detectors re-baseline after N consecutive anomalies, or keep a slower second EWMA and alert on the gap between them.
- Datadog's anomaly monitors, Prometheus `holt_winters` / `predict_linear`, and most AIOps tools are this idea plus seasonality. Daily traffic cycles need a seasonal baseline (same minute last week) or the morning ramp is "anomalous" every day.
- Run detectors on rates and percentiles, not raw counts, and gate on volume: a p95 over 3 requests is noise.
- Use this for the "something changed" signal and `slo-burn-rate-alerts` (139) for the "users are hurting" page. `streaming-latency-percentiles` (138) produces the p95 series this consumes.
