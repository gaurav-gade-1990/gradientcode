Your embeddings endpoint reports its p95 latency once a minute, and you want an alert when a minute looks unlike the recent past without hand-tuning a static threshold for every model. Implement a streaming EWMA detector.

```python
class EwmaDetector:
    def __init__(self, alpha, k, warmup, min_std): ...
    def update(self, value) -> dict: ...   # {"z": float or None, "anomaly": bool}
    # attributes read by the judge after every update: self.mean, self.var
```

The detector keeps an exponentially weighted mean and variance. Process each `value` $x$ (index $i = 0, 1, \dots$) like this:

| step | rule |
|---|---|
| first point ($i = 0$) | `mean = x`, `var = 0.0`. Return `{"z": None, "anomaly": False}`. |
| warmup ($1 \le i <$ `warmup`) | Don't score. Update the baseline (below). Return `{"z": None, "anomaly": False}`. |
| after warmup | Score against the baseline **before** this point: $z = \dfrac{x - \text{mean}}{\max(\sqrt{\text{var}},\ \text{min\_std})}$. The point is anomalous when $\lvert z \rvert > k$ (strict). |
| | Not anomalous: update the baseline. Anomalous: leave `mean` and `var` unchanged. |
| | Return `{"z": z, "anomaly": bool}`. |

The baseline update is the incremental EWMA (Finch, 2009):

$$
d = x - \text{mean},\qquad \text{mean} \leftarrow \text{mean} + \alpha d,\qquad \text{var} \leftarrow (1 - \alpha)\,(\text{var} + \alpha d^2)
$$

`warmup` counts the first point, so `warmup = 1` scores from index 1 onward.

The judge feeds the series one value at a time and records, for every point, the returned `z`, the anomaly flag, and your `mean` and `var` right after the call. It also lists the anomalous indices.

**Constraints**

- `0 < alpha < 1`, `k > 0`, `min_std > 0`, `1 <= warmup <= len(series)`
- `1 <= len(series) <= 2000`; values are latencies in milliseconds
- Use only floats and the stdlib; compared with relative tolerance `1e-6`
