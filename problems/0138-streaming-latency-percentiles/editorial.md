## Approach

Exact percentiles need every sample. A relative-error sketch keeps one counter per **log-spaced** bucket instead. With $\gamma = \frac{1+\alpha}{1-\alpha}$, bucket $i$ covers $(\gamma^{i-1}, \gamma^i]$, and its representative $\frac{2\gamma^i}{\gamma+1}$ is within relative error $\alpha$ of every value in it. Going from 1 ms to 10 minutes takes only $\ln(600000)/\ln\gamma \approx 660$ buckets at $\alpha = 1\%$.

```python
def record(self, v, count=1):
    validate count and v first             # nothing is mutated on a bad input
    if v == 0: self._zero += count; return
    i = math.ceil(math.log(v) / self._log_gamma)
    self._counts[i] = self._counts.get(i, 0) + count
    self._collapse()

def merge(self, other):
    for i, c in other._counts.items():     # counts add, which is why sketches merge
        self._counts[i] = self._counts.get(i, 0) + c
    self._zero += other._zero

def quantile(self, q):
    rank = q * (n - 1); cum = zero bucket, then ascending buckets
    return the representative of the first bucket with cum > rank
```

The key property is **mergeability**: the histogram of the union is the sum of the histograms, so a collector can add per-replica sketches and get the exact sketch of the fleet. Averaging per-replica p99s is wrong, because a quiet replica with a slow tail and a busy healthy one don't average to the fleet's p99.

When memory is capped, fold the **lowest** buckets upward. Low quantiles lose accuracy, and p99 stays exact to $\alpha$.

## Common mistakes

- **Overwriting instead of adding on merge** (`dict.update`). The fleet sketch then holds only one replica's counts per bucket.
- **Aliasing the source's dict** when merging into an empty histogram. Later records to the replica leak into the collector and get double counted.
- **`floor` instead of `ceil`.** Every value lands one bucket low, and p99 reads about $2\alpha$ too optimistic.
- **Folding the high buckets** under the cap. The tail you are paging on disappears into lower buckets.
- **Clamping negatives to zero.** Negative latencies mean clock skew (for example a non-monotonic clock across hosts). Reject them and count the rejections; don't let them pose as cache hits.
- **Rank off by one.** `rank = q * (n - 1)` with a strict `cum > rank` gives p0 = the minimum and p100 = the maximum.

## Production notes

- This is DDSketch (Datadog), used in Datadog's agents and in OpenTelemetry's **exponential histogram**, whose base-2 scale factor is the same idea with $\gamma = 2^{2^{-\text{scale}}}$. Prometheus native histograms use the same layout. HdrHistogram (log buckets with linear sub-buckets) and t-digest are the other common choices. t-digest is accurate at the extremes but is not exactly mergeable.
- Use a monotonic clock (`time.monotonic()`, `CLOCK_MONOTONIC`) for latency. Wall-clock deltas go negative on NTP corrections.
- Ship bucket deltas per scrape interval, not cumulative quantiles, so the backend can re-aggregate across any set of pods and any time range.
- Percentiles of LLM calls are bimodal: cache hits, short completions and long generations. Track TTFT and total latency in separate histograms, and per model.
- Pair with `slo-burn-rate-alerts` (139), which turns these counts into error-budget burn, and `load-balancer-p2c` (132), whose p99 comparison is exactly a merge of per-replica histograms.
