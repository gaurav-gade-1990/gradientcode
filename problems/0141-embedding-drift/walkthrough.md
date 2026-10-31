## 1. What the problem is really asking

Strip away the support-ticket story and this is a **two-sample test on point clouds**, computed two ways:

> have this week's embeddings moved? Check the cheap way (do the two windows' mean vectors point the same direction?) and the thorough way (do the two clouds look the same under a kernel?), then report which checks crossed their thresholds.

There are three numbers to compute, and each is a short NumPy expression once you know its definition:

- **Centroid cosine distance**: `1 - cos(mean(ref), mean(cur))`. One vector per window, O(n·d).
- **Sigma**: the RBF bandwidth, from the **median heuristic** over the pooled sample.
- **MMD²**: the **unbiased** maximum mean discrepancy with that bandwidth. Average kernel similarity within `ref`, plus within `cur`, minus twice across.

Then two threshold checks become `reasons`, and `drifted` is `bool(reasons)`.

The judge's driver turns ticket text into vectors with `gc_runtime.embed(text, dim=32)`, calls your function, and grades all five keys: three floats with relative tolerance `1e-6`, the bool, and the `reasons` list in order. So `sigma` is graded on its own. A bandwidth that's slightly off fails even if both checks happen to come out right.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `ref` | `(n, d)` array, the reference window | row mean `mu_r`; the `x` sample in MMD |
| `cur` | `(m, d)` array, this week's window | row mean `mu_c`; the `y` sample |
| `cos_threshold` | float | `"centroid_shift"` if the cosine distance is strictly above it |
| `mmd_threshold` | float | `"mmd"` if `mmd2` is strictly above it |

`n` and `m` are between 2 and 60, and `d = 32`. The judge's `embed` is a hashed bag of words: each word adds +1 or -1 to one of 32 slots, and the vector is L2-normalized. Tickets that share words have similar vectors. Tickets with no words in common are close to orthogonal, and two orthogonal unit vectors are `sqrt(2) = 1.41421` apart. That's why many tests have `sigma` exactly 1.41421.

Three details are easy to miss:

- **An empty ticket embeds to all zeros**, not a unit vector. A window of empty tickets has a centroid of norm 0, and the cosine is undefined. The rule says to use `1.0`.
- **The cosine distance can exceed 1.** If the centroids point slightly away from each other, the cosine is negative. Example 2 gives 1.23503. Don't clip it.
- **`mmd2` can be negative.** The unbiased estimator is centred on 0 when nothing changed, so when nothing changed, noise often makes it slightly negative. Return it as is.

## 3. Trace Example 3 by hand

This one is small enough to do on paper. `ref = [A, B]` and `cur = [A, B]`, the same two login tickets. Call `d = ||A - B||`.

**Centroid.** Both means are `(A + B) / 2`, so the cosine is 1 and the distance is **0**.

**Sigma.** Stack into `Z = [A, B, A, B]`, 4 rows. There are `4·3/2 = 6` unordered pairs:

| pair | distance |
|---|---|
| A–B (ref), A'–B' (cur), A–B', B–A' | d |
| A–A', B–B' | 0 |

The six values sorted are `0, 0, d, d, d, d`. The median (mean of the 3rd and 4th) is `d`, so `sigma = d = 1.20857`.

**MMD².** With `sigma = d`, `k(A, B) = exp(-d² / (2d²)) = exp(-1/2) = 0.6065`, and `k(A, A) = 1`.

| term | which pairs | value |
|---|---|---|
| within `ref`, `i ≠ j`, divided by `n(n-1) = 2` | (A,B), (B,A) | `2·0.6065 / 2 = 0.6065` |
| within `cur`, same | (A,B), (B,A) | `0.6065` |
| cross, all `n·m = 4` pairs, times 2 | (A,A), (A,B), (B,A), (B,B) | `2 · (1 + 1 + 0.6065 + 0.6065) / 4 = 1.6065` |

`mmd2 = 0.6065 + 0.6065 - 1.6065 = exp(-1/2) - 1 = -0.393469`. Identical windows give a **negative** MMD², because the cross term includes the perfect self-matches A–A' and B–B', while the within terms are forbidden from using the diagonal. Neither threshold fires, so `reasons = []`.

### Example 1 and Example 2 side by side

Both have the same 8-ticket reference (4 billing, 4 login). Example 1's current window is different billing and login tickets. Example 2's is 8 SSO tickets.

| | Example 1 | Example 2 |
|---|---|---|
| `centroid_cosine_distance` | 0.384533 (under 0.45) | **1.23503** |
| `sigma` | 1.33001 | 1.41421 |
| mean `K_xx` (off-diagonal) | 0.5985 | 0.6349 |
| mean `K_yy` (off-diagonal) | 0.5963 | 0.6378 |
| mean `K_xy` | 0.6142 | 0.5942 |
| `mmd2` | 0.5985 + 0.5963 - 2·0.6142 = **-0.033724** | 0.6349 + 0.6378 - 2·0.5942 = **0.0842787** |
| `reasons` | `[]` | `["centroid_shift", "mmd"]` |

In Example 1 a reference ticket is about as similar to a current ticket as it is to another reference ticket. In Example 2 the cross similarity drops below both within-window similarities, and that gap is the MMD.

## 4. Key idea: why two statistics

The centroid check only sees the mean. Two hidden cases show what each statistic misses:

- **"bot replays two tickets"**: the current window is the same two tickets six times over. Its mean sits between billing and login, so the centroid distance is only 0.49021 (under 0.6). But the current cloud has collapsed onto two points: mean `K_yy` is 0.7854 against 0.6326 for the reference. MMD² is 0.105508, and only `"mmd"` fires.
- **"half the week is the new topic"**: four billing tickets plus four SSO tickets. The mean moves (0.642889, so `"centroid_shift"` fires), but every kernel average stays near 0.63, and MMD² is -0.00147. With only 8 current tickets the kernel test has little power.

Neither statistic is enough alone, so the report gives both.

## 5. Key idea: the median heuristic, done exactly

The RBF kernel `exp(-||x - y||² / (2σ²))` is useless if `σ` is far from the typical distance. Too wide and every similarity is about 1; too narrow and every off-diagonal similarity is about 0. The median of pairwise distances puts the typical pair at `exp(-1/2)`.

The problem pins down exactly which distances to use:

- **Pooled**: `ref` and `cur` stacked, so `σ` reflects the distances the test will measure, including the cross distances.
- **Unordered pairs `i < j`**: `np.triu_indices(n + m, k=1)` picks the strict upper triangle, so each pair appears once and the diagonal zeros are left out.

If you take the median of the full `(n+m) × (n+m)` matrix, you add `n + m` zeros, which pulls the median down. In Example 3 it drops `sigma` to 0.604285 and makes `mmd2` -0.864665.

## 6. Key idea: unbiased means no diagonal

`k(x_i, x_i) = 1` always. The biased estimator averages the full `K_xx`, diagonal included, which adds roughly `1/n + 1/m` to every score, and more for small windows. The unbiased one removes the diagonal and divides by `n(n-1)`:

```
within_x = (K_xx.sum() - trace(K_xx)) / (n * (n - 1))
```

The cross term has no diagonal to remove (an `x` and a `y` are different samples), so it is a plain mean over all `n·m` entries. In Example 1 the biased version gives `mmd2 = 0.0669` instead of -0.0337 and wrongly reports `"mmd"`.

## 7. Plan before you code

```
x, y = arrays; n, m = row counts
centroids: mx, my = row means; if either norm is 0: cos_dist = 1.0, else 1 - cosine
sigma: Z = stack(x, y); D = pairwise distances of Z; median over the strict upper triangle; 0 -> 1.0
kernel: k(a, b) = exp(-sqdist(a, b) / (2 sigma^2))
mmd2 = off-diagonal mean of K_xx + off-diagonal mean of K_yy - 2 * mean of K_xy
reasons: "centroid_shift" if cos_dist > cos_threshold, then "mmd" if mmd2 > mmd_threshold
return the five keys
```

## 8. Build it one piece at a time

**Step 1: pairwise squared distances without loops.** `||a - b||² = ||a||² + ||b||² - 2 a·b`. Shapes: `(p, 1) + (1, q) - (p, q)` broadcasts to `(p, q)`. Floating-point rounding can make a true 0 come out as `-1e-16`, and `sqrt` of that is `nan`, so clip at 0.

```python
def _sqdist(a, b):
    d = (a * a).sum(1)[:, None] + (b * b).sum(1)[None, :] - 2.0 * a @ b.T  # (p, q)
    return np.maximum(d, 0.0)
```

**Step 2: centroid distance with the zero guard.** Without the guard, "ingestion bug sends empty bodies" divides by 0, gets `nan`, and `nan > 0.2` is False, so `"centroid_shift"` silently disappears.

```python
mx, my = x.mean(0), y.mean(0)            # (d,), (d,)
nx, ny = np.linalg.norm(mx), np.linalg.norm(my)
cos_dist = 1.0 if nx == 0 or ny == 0 else 1.0 - float(mx @ my / (nx * ny))
```

**Step 3: the bandwidth.** `np.median` of an even count already averages the two middle values.

```python
z = np.vstack([x, y])                    # (n + m, d)
iu = np.triu_indices(len(z), k=1)        # each unordered pair once
sigma = float(np.median(np.sqrt(_sqdist(z, z)[iu])))
```

**Step 4: the three kernel blocks and the unbiased combination.**

```python
kxx, kyy, kxy = k(x, x), k(y, y), k(x, y)    # (n, n), (m, m), (n, m)
mmd2 = ((kxx.sum() - np.trace(kxx)) / (n * (n - 1))
        + (kyy.sum() - np.trace(kyy)) / (m * (m - 1))
        - 2.0 * kxy.mean())
```

`n, m >= 2` by the constraints, so `n(n-1)` is never 0.

## 9. Full solution

```python
import numpy as np  # vectorized distances and kernel matrices


# Squared Euclidean distance between every row of a and every row of b.
def _sqdist(a, b):
    d = (a * a).sum(1)[:, None] + (b * b).sum(1)[None, :] - 2.0 * a @ b.T  # |a|^2 + |b|^2 - 2a.b, shape (p, q)
    return np.maximum(d, 0.0)  # rounding can give tiny negatives; sqrt of those would be nan


# Compare two windows of embeddings by centroid direction and by unbiased MMD.
def embedding_drift(ref, cur, cos_threshold, mmd_threshold):
    x, y = np.asarray(ref, dtype=float), np.asarray(cur, dtype=float)  # (n, d) and (m, d) float arrays
    n, m = len(x), len(y)  # window sizes, needed for the unbiased denominators

    mx, my = x.mean(0), y.mean(0)  # each window's centroid, shape (d,)
    nx, ny = np.linalg.norm(mx), np.linalg.norm(my)  # centroid lengths for the cosine
    # An all-zero centroid (empty tickets) has no direction, so count it as fully shifted.
    cos_dist = 1.0 if nx == 0 or ny == 0 else 1.0 - float(mx @ my / (nx * ny))

    z = np.vstack([x, y])  # pool both windows so sigma reflects cross distances too
    iu = np.triu_indices(len(z), k=1)  # strict upper triangle: each unordered pair once, no self-pairs
    sigma = float(np.median(np.sqrt(_sqdist(z, z)[iu])))  # median heuristic for the RBF bandwidth
    # Every pooled point identical: a zero bandwidth would divide by zero.
    if sigma == 0:
        sigma = 1.0  # fall back to a unit bandwidth

    # RBF kernel matrix between the rows of a and b.
    def k(a, b):
        return np.exp(-_sqdist(a, b) / (2.0 * sigma ** 2))  # 1 for identical rows, toward 0 for distant ones

    kxx, kyy, kxy = k(x, x), k(y, y), k(x, y)  # within-ref, within-cur and cross similarity matrices
    # Unbiased MMD^2: drop the diagonals of the within terms, keep every cross pair.
    mmd2 = ((kxx.sum() - np.trace(kxx)) / (n * (n - 1))
            + (kyy.sum() - np.trace(kyy)) / (m * (m - 1))
            - 2.0 * kxy.mean())

    reasons = []  # which checks fired, in the required order
    # The windows' mean directions moved apart.
    if cos_dist > cos_threshold:
        reasons.append("centroid_shift")  # checked first, so listed first
    # The distributions differ beyond what the threshold tolerates.
    if mmd2 > mmd_threshold:
        reasons.append("mmd")  # listed second
    # Plain Python floats and a bool, with drifted derived from the reasons.
    return {"centroid_cosine_distance": cos_dist, "sigma": sigma, "mmd2": float(mmd2),
            "drifted": bool(reasons), "reasons": reasons}
```

## 10. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | distance 0.384533, mmd2 -0.033724, no drift | same topics, new phrasing: both statistics stay low |
| Example 2 | distance 1.23503, mmd2 0.0842787, both reasons | a new topic moves the centroid and lowers cross similarity |
| Example 3 | distance 0, sigma 1.20857, mmd2 -0.393469 | self-pairs excluded from the median; unbiased MMD is negative for identical windows |
| large windows same mix | distance 0.123239, mmd2 -0.00523648, no drift | 40 vs 36 tickets from the same mix: no false alarm |
| large windows SSO launch | both reasons, mmd2 0.0300721 | a half-SSO week at realistic window sizes |
| topic mix shift | `["centroid_shift"]`, mmd2 0.0176 just under 0.02 | the same topics in different proportions |
| ingestion bug sends empty bodies | distance 1, sigma 1, both reasons | the zero-norm centroid rule |
| uneven window sizes | `["centroid_shift"]`, mmd2 0.0478588 | `n = 14`, `m = 3`: the separate `n(n-1)` and `m(m-1)` denominators |
| half the week is the new topic | `["centroid_shift"]`, mmd2 -0.00147319 | the centroid catches what a small-sample MMD misses |
| bot replays two tickets | `["mmd"]`, distance 0.49021 | MMD catches a collapse that keeps the mean in place |
| high thresholds never fire | distance 1.04299, mmd2 0.0615949, no drift | thresholds come from the arguments; distance above 1 isn't clipped |

## 11. Complexity

With `N = n + m` pooled rows and dimension `d`, the pooled distance matrix is O(N²·d) time and O(N²) memory, and the three kernel blocks cost the same again. The centroid check is O(N·d). At `N ≤ 120` and `d = 32` this is a few matrix multiplies, well under a millisecond.

In production the quadratic term is what bites. A week of 200,000 tickets would need a 4·10¹⁰-entry matrix. Subsample a few thousand rows per window, or approximate the RBF kernel with random Fourier features, which makes MMD linear in `N`. The centroid check scales to any volume, which is why dashboards usually show it, with MMD run on samples.

## 12. If you got Wrong Answer

Compare `sigma` first. It feeds `mmd2`, so a wrong bandwidth makes both numbers wrong.

- **In Example 3, `sigma` is 0.604285 instead of 1.20857 and `mmd2` is -0.864665.** You took the median of the full distance matrix, including the zero diagonal and each pair twice. Use the strict upper triangle.
- **In Example 2, `sigma` is 1.33054 instead of 1.41421.** You computed the bandwidth from `ref` alone. Stack both windows first.
- **In Example 1, `mmd2` is 0.0669 and `"mmd"` fires.** You used the biased estimator. Subtract the trace and divide by `n(n-1)` and `m(m-1)`. In Example 3 the biased version gives exactly 0.
- **In "ingestion bug sends empty bodies", the distance is `nan` and `reasons` is only `["mmd"]`.** You divided by a zero centroid norm. Return 1.0 when either norm is 0.
- **`sigma` is `nan` in the large-window cases and "bot replays two tickets".** Repeated tickets have a true distance of 0, which rounding turns into a tiny negative number, and its `sqrt` is `nan`. Clip with `np.maximum(d, 0.0)`.
- **`reasons` is `["mmd", "centroid_shift"]`.** Check the centroid first.

## 13. Follow-ups an interviewer might ask

- *How do you choose the thresholds?* MMD values have no universal scale. Build a null distribution: split historical reference data into pairs of windows of the real sizes, compute MMD² for each pair, and set the threshold at a high percentile. A permutation test (shuffle the pooled rows into fake windows) gives a p-value for one comparison.
- *How do you scale this to a million embeddings a week?* Subsample, use random Fourier features for a linear-time MMD, or train a small domain classifier to tell `ref` from `cur`. An AUC near 0.5 means no drift.
- *What about scalar features like ticket length?* Use a per-feature test: a KS test (problem 136, ks-drift-detector) or PSI over bins (problem 135, population-stability-index).
- *What happens when you upgrade the embedding model?* Every vector changes, so the detector reports drift on the first night. Re-embed the reference window with the new model and reset the baseline at the same time.
- *What do you do when it fires?* Cluster the current window and look at the clusters far from the reference. A new topic usually needs new routing rules or labels. A cache keyed on embeddings (problem 127, semantic-cache) also loses hit rate when inputs drift.
