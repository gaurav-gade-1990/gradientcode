## Approach

Embedding drift asks whether this week's inputs live in the same region of embedding space as the reference window. Two complementary statistics:

**Centroid shift** is the cosine distance between the window means. It is O(nd), easy to explain on a dashboard, and catches a whole-population move such as a new topic. It is blind to anything that keeps the mean in place: a window that collapses onto two repeated tickets, or one topic swapped for its "opposite".

**MMD** (maximum mean discrepancy) compares the full distributions through a kernel. With an RBF kernel it is 0 in expectation exactly when the distributions match. The unbiased estimator drops the $k(x_i, x_i) = 1$ diagonal terms:

$$
\widehat{\text{MMD}}^2 = \overline{K_{xx}}_{i \ne j} + \overline{K_{yy}}_{i \ne j} - 2\,\overline{K_{xy}}
$$

The bandwidth matters more than the kernel. The **median heuristic** sets $\sigma$ to the median pairwise distance over the pooled sample, so the kernel is neither ~1 everywhere (too wide) nor ~0 off the diagonal (too narrow).

```python
z = np.vstack([x, y])
iu = np.triu_indices(len(z), k=1)                   # each unordered pair once
sigma = float(np.median(np.sqrt(_sqdist(z, z)[iu]))) or 1.0
k = lambda a, b: np.exp(-_sqdist(a, b) / (2 * sigma ** 2))
kxx, kyy, kxy = k(x, x), k(y, y), k(x, y)
mmd2 = ((kxx.sum() - np.trace(kxx)) / (n * (n - 1))
        + (kyy.sum() - np.trace(kyy)) / (m * (m - 1))
        - 2 * kxy.mean())
```

`_sqdist` uses $\lVert a\rVert^2 + \lVert b\rVert^2 - 2a\cdot b$ and clips at 0, which is O((n+m)^2 d) with one matrix multiply.

## Common mistakes

- **The biased estimator.** Keeping the diagonal adds roughly $1/n + 1/m$ to every score, so small windows always look drifted, and the bias changes with the window size.
- **Self-pairs in the median.** Taking the median of the full distance matrix mixes in $n + m$ zeros, which shrinks $\sigma$ and makes the kernel too sharp.
- **Bandwidth from the reference only.** It looks fine until the current window is far away, then $\sigma$ no longer reflects the distances you are measuring.
- **Thresholding a single number without a null.** MMD values have no universal scale; calibrate thresholds by comparing reference windows against each other.

## Production notes

- Evidently, Arize, WhyLabs and Fiddler all ship embedding drift built from these pieces (centroid distance, MMD or a domain classifier). Alibi Detect's `MMDDrift` adds a permutation test for a p-value, which is what you would add here at scale.
- The pairwise cost is quadratic: subsample to a few thousand rows, or use random Fourier features for a linear-time MMD.
- Embed with the same model version you serve with. An embedding model upgrade is itself "drift" and should reset the reference window.
- Pair with `ks-drift-detector` (136) and `population-stability-index` (135) for scalar features, and use drifted clusters to trigger re-labeling or a routing review. `semantic-cache` (127) is hit hardest by this kind of shift.
