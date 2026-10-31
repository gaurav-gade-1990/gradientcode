Your inference API runs on many replicas, and the SLO dashboard needs a fleet-wide p99. You can't ship every latency sample to one place, and the p99s of the replicas can't be averaged. Each replica keeps a small log-bucket histogram (a DDSketch-style "HDR-lite") with a bounded **relative** error, and the collector merges them. Implement it.

```python
class LatencyHistogram:
    def __init__(self, alpha=0.01, max_buckets=2048): ...
    def record(self, value_ms, count=1): ...
    def merge(self, other): ...
    def quantile(self, q): ...
    def count(self): ...
    def buckets(self): ...
```

**Buckets.** Let $\gamma = \dfrac{1 + \alpha}{1 - \alpha}$. A positive value $v$ goes to bucket

$$
i = \left\lceil \frac{\ln v}{\ln \gamma} \right\rceil
$$

computed exactly as `math.ceil(math.log(v) / math.log(gamma))`. Bucket $i$ covers $(\gamma^{i-1}, \gamma^i]$ and its representative value is $\dfrac{2\gamma^i}{\gamma + 1}$, which is within a relative error of $\alpha$ of every value in the bucket. A value of exactly `0` (a cache hit) goes to a separate **zero bucket** whose representative is `0.0`.

| method | contract |
|---|---|
| `record(value_ms, count=1)` | Add `count` observations of `value_ms`. Raise `ValueError` and record **nothing** if `value_ms < 0` (clock skew) or `count` is not an int `>= 1`. |
| `merge(other)` | Add every bucket count and the zero count of `other` into `self`. Raise `ValueError` if `other.alpha != self.alpha`. `other` must be left unchanged, and later changes to either histogram must not affect the other. |
| `quantile(q)` | Raise `ValueError` unless `0 <= q <= 1`. Return `None` when the histogram is empty. Otherwise let `n = count()` and `rank = q * (n - 1)`. Walk the zero bucket first, then the buckets in increasing index, and return the representative of the first bucket whose cumulative count is `> rank`. |
| `count()` | The total number of observations, including zeros. |
| `buckets()` | A list of `[index, count]` pairs for the non-empty buckets, sorted by index. The zero bucket is not included. |

**Memory bound.** After every `record` and `merge`, while there are more than `max_buckets` non-empty buckets, fold the **lowest-index** bucket into the next-lowest one (add its count there and remove it). This keeps the high percentiles accurate, which is what the SLO cares about. The zero bucket never counts toward or takes part in folding.

The judge drives your class with per-replica latency streams, merges, and quantile queries, and records every result, every `ValueError`, and the bucket table after each step.

**Constraints**

- `0 < alpha < 0.5`, `1 <= max_buckets <= 4096`
- Latencies are floats in `[0, 600000]` ms
- At most 5000 observations per test
