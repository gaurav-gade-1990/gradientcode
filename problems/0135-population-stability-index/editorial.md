## Approach

PSI compares how a feature's mass is spread across fixed buckets in two windows. The buckets are the reference deciles, so every reference bin holds about 10% of the traffic and any movement shows up as bins that gained or lost share.

1. Fit the bins on the **reference** only: interior cut points at the quantiles $1/n, \dots, (n-1)/n$, deduplicated.
2. Count each window into the same right-closed bins. `np.searchsorted(edges, x, side="left")` returns the first edge `>= x`, which is exactly "bin $j$ is $(e_{j-1}, e_j]$".
3. Floor every proportion at `eps` so an empty bin gives a large but finite term instead of $\ln 0$.
4. Sum $(c_j - r_j)\ln(c_j / r_j)$. Each term is non-negative, because the two factors always share a sign. That is why PSI is a symmetric, KL-like divergence.

```python
edges = np.unique(np.quantile(ref, [i / n_bins for i in range(1, n_bins)]))
B = len(edges) + 1
r = np.maximum(np.bincount(np.searchsorted(edges, ref, side="left"), minlength=B) / len(ref), eps)
c = np.maximum(np.bincount(np.searchsorted(edges, cur, side="left"), minlength=B) / len(cur), eps)
contrib = (c - r) * np.log(c / r)
```

The `top_bin` field is the one the on-call actually reads: it says *where* the distribution moved (for example "the top decile of prompt length doubled").

## Common mistakes

- **Refitting the bins on the current window.** Every current bin then holds 1/n by construction, and PSI only measures how the *reference* looks in today's bins. A doubled prompt length can still look stable.
- **No epsilon.** One empty bin makes PSI `inf`, or `NaN` when both sides are empty. A `psi >= 0.25` alert is false for NaN, so the page never fires.
- **Left-closed bins.** With `side="right"`, values equal to an edge move up a bin. Integer features (token counts, retries) sit on edges constantly, so this alone shows drift between two identical days.
- **Keeping duplicate edges.** Tied features produce repeated quantiles. Zero-width bins inflate the bin count and misreport the per-bin table.
- **Sorting the input in place.** The job shares one reference array across features and days, so an in-place sort corrupts the caller's data.

## Production notes

- The 0.1 / 0.25 bands come from credit-risk scorecards. They are a convention, not a test statistic. PSI grows with the number of bins and shrinks with sample size, so tune the bands per feature or pair PSI with a KS test (problem 136), which does have a p-value.
- Store the reference **edges** with the model version in the feature store or model registry. Recomputing them from a moving reference makes yesterday's PSI incomparable to today's.
- Evidently, WhyLabs, Arize and SageMaker Model Monitor all ship PSI with quantile binning and an epsilon floor. Evidently's default epsilon is 1e-4, as here.
- For categorical features, use one bin per category plus an "other" bin for unseen values. A new category is drift you want to see.
- At scale, compute counts in the warehouse (`width_bucket` in SQL, or a Spark UDF) and only the tiny count vectors reach the PSI code. Pair with `embedding-drift` (141) for unstructured inputs and `train-serve-skew` (150) for pipeline bugs.
