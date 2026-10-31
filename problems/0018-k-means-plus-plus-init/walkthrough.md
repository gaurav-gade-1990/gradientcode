## 1. What the problem is really asking

Lloyd's algorithm (problem 17, k-means) only finds a local minimum, and which one depends on where the centroids start. Pick two starting points inside the same blob and one cluster gets split while two others get merged, no matter how long you iterate. k-means++ fixes the start: it picks seeds that are spread out, by preferring points far from every seed chosen so far.

Under the story, this is **weighted sampling without a random generator**. You're handed the uniforms `u`, so each draw becomes a deterministic lookup: build a cumulative sum of weights and find where `u[j]` times the total falls. That technique is **inverse-CDF sampling**, and with `np.cumsum` plus `np.searchsorted` it's two lines.

The judge compares your `(k,)` index array exactly (`rtol = 0`, `atol = 0`). One index off and the case fails. So the details of the boundary rule (strictly greater, `side="right"`) are not cosmetic.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `X` | `(n, d)` | the points to seed from | you return row indices into it |
| `k` | int, `1 <= k <= n` | how many seeds | the number of draws |
| `u` | `(k,)`, each in `[0, 1)` | pre-drawn uniforms, one per seed | `u[0]` picks the first seed, `u[j]` the `j`-th |
| return | `(k,)` int | chosen indices, in order | compared exactly |

Three details are easy to miss:

- **The first seed is uniform, not weighted.** $c_0 = \lfloor u_0 n \rfloor$. There are no chosen centers yet, so there's no distance to weight by.
- **$D^2$ is the distance to the nearest chosen center**, not to the newest one. After three seeds, a point next to seed 0 must have a small weight even if it's far from seed 2.
- **The weight is squared distance.** Plain distance gives different probabilities and a different pick on several tests.

## 3. The math

After choosing centers $C = \{c_0, \dots, c_{j-1}\}$, each point gets a weight

$$
D^2_i = \min_{c \in C} \lVert x_i - x_c \rVert^2, \qquad i = 0, \dots, n-1 .
$$

k-means++ picks the next center $c_j = i$ with probability

$$
P(c_j = i) = \frac{D^2_i}{\sum_{l=0}^{n-1} D^2_l} .
$$

**Why inverse-CDF sampling gives exactly this.** Let $S_i = \sum_{l \le i} D^2_l$ be the cumulative sum, with $S_{-1} = 0$ and total $S_{n-1}$. Draw $u \sim \text{Uniform}[0, 1)$ and set $\tau = u\, S_{n-1}$, which is uniform on $[0, S_{n-1})$. The rule "pick the smallest $i$ with $S_i > \tau$" picks $i$ exactly when $S_{i-1} \le \tau < S_i$. That interval has length $S_i - S_{i-1} = D^2_i$, so

$$
P(c_j = i) = \frac{S_i - S_{i-1}}{S_{n-1}} = \frac{D^2_i}{S_{n-1}} .
$$

The interval view also explains the boundary rule. A point with $D^2_i = 0$ (a chosen center, or a duplicate of one) has $S_i = S_{i-1}$, an **empty** interval $[S_{i-1}, S_i)$. With the strict $S_i > \tau$, no $\tau$ can select it. With $\ge$ (`side="left"`), a $\tau$ exactly equal to $S_i$ would land on the left end of a flat step and pick it.

**Why squared distance.** The k-means objective is a sum of squared distances, so $D^2_i$ is exactly the cost point $i$ currently pays. Sampling in proportion to cost puts the next seed where the clustering is worst. Arthur and Vassilvitskii proved this gives an expected cost within $O(\log k)$ of the optimum, before Lloyd's algorithm even runs. Plain distance has no such guarantee.

**Keeping $D^2$ up to date.** Adding a new center $c$ can only shrink each point's nearest-center distance:

$$
D^2_i \leftarrow \min\!\big(D^2_i,\; \lVert x_i - x_c \rVert^2\big).
$$

So you keep one running array and never recompute distances to old centers.

## 4. Trace an example by hand

**Example 2.** `X` is `(4, 2)`: `(0, 0), (1, 0), (0, 2), (5, 5)`. `k = 3`, `u = [0.6, 0.0, 0.99]`.

**Seed 0.** $\lfloor 0.6 \cdot 4 \rfloor = 2$, the point `(0, 2)`.

| draw | $D^2$ (shape `(4,)`) | $S$ | $\tau = u_j S_3$ | first $S_i > \tau$ |
|---|---|---|---|---|
| $j = 1$, $u = 0.0$ | `[4, 5, 0, 34]` | `[4, 9, 9, 43]` | 0.0 | index 0 |
| $j = 2$, $u = 0.99$ | `[0, 1, 0, 34]` | `[0, 1, 1, 35]` | 34.65 | index 3 |

After seed 0 is added, `D2[0]` drops from 4 to 0 (the running minimum), and `D2[1]` drops from 5 to 1 because `(1, 0)` is closer to `(0, 0)` than to `(0, 2)`. The result is `[2, 0, 3]`.

**The hidden "u zero after first center" case** shows the zero-weight rule. `X` is `2, 0, 5, 9` in 1-D, `u = [0, 0, 0]`. Seed 0 is index 0 (the point 2).

| draw | $D^2$ | $S$ | $\tau$ | `side="right"` | `side="left"` |
|---|---|---|---|---|---|
| $j = 1$ | `[0, 4, 9, 49]` | `[0, 4, 13, 62]` | 0.0 | **1** | 0 |
| $j = 2$ | `[0, 0, 9, 49]` | `[0, 0, 9, 58]` | 0.0 | **2** | 0 |

With `side="left"`, $\tau = 0$ matches $S_0 = 0$ and index 0, the center already chosen, is picked again, twice. The expected output is `[0, 1, 2]`.

**"target on a boundary"** is the same rule at a nonzero step. `X` is `0, 1, 2, 3`, `u = [0, 1/14]`. With seed 0 at index 0, $D^2 = [0, 1, 4, 9]$, $S = [0, 1, 5, 14]$, and $\tau = 14/14 = 1.0$ exactly. $S_1 = 1$ is not *strictly* greater than 1, so the answer is index 2. `side="left"` returns 1.

## 5. Key idea: `searchsorted(side="right")` is the strict inequality

`np.searchsorted(a, v, side=...)` assumes `a` is sorted ascending and returns the position where `v` would be inserted to keep it sorted:

| `side` | returns the smallest `i` with | on a tie with `a[i] == v` |
|---|---|---|
| `"left"` (default) | `a[i] >= v` | lands *on* the tie |
| `"right"` | `a[i] > v` | lands *after* every tie |

The cumulative sum is non-decreasing because every $D^2_i \ge 0$, so `searchsorted` is valid on it. The spec's rule, "smallest $i$ with $S_i > \tau$", is word for word the `side="right"` row. The default `side="left"` is the bug.

## 6. Plan before you code

```
n = number of rows
idx = [floor(u[0] * n)]                         # first seed: uniform
D2 = squared distance from every point to X[idx[0]]   # (n,)
for j in 1 .. k-1:
    S = cumulative sum of D2                    # (n,)
    tau = u[j] * S[-1]
    c = first index with S > tau                # searchsorted, side="right"
    append c
    D2 = elementwise min(D2, squared distance to X[c])
return idx as an int array
```

## 7. Build it one piece at a time

**Step 1: the first seed and its distances.**

```python
n = X.shape[0]
idx = [min(int(np.floor(u[0] * n)), n - 1)]
D2 = np.sum((X - X[idx[0]]) ** 2, axis=1)        # (n, d) - (d,) -> (n, d) -> (n,)
```

`X[idx[0]]` is one row with shape `(d,)`. Subtracting it from `(n, d)` broadcasts it across every row: NumPy lines up trailing axes, `d` matches `d`, and the missing leading axis is stretched to `n`. The `min(..., n - 1)` is purely defensive. For `u[0] < 1` the product `u[0] * n` stays below `n` in floating point too (even the largest double below 1, times any `n` up to 500, floors to at most `n - 1`), so the clamp never fires here, but it costs nothing and protects against a caller passing `u[0] = 1.0`.

**Step 2: one weighted draw.**

```python
cum = np.cumsum(D2)                                         # (n,), non-decreasing
c = int(np.searchsorted(cum, u[j] * cum[-1], side="right"))  # scalar index
```

`cum[-1]` is the total weight, so `u[j] * cum[-1]` is $\tau$. Because $\tau < S_{n-1}$ whenever $u_j < 1$, `searchsorted` returns at most `n - 1`, a valid index. The constraint "at least `k` distinct rows" guarantees the total is positive at every step: there's always an unchosen point with $D^2 > 0$.

**Step 3: update the running minimum.**

```python
D2 = np.minimum(D2, np.sum((X - X[c]) ** 2, axis=1))  # (n,) elementwise min with the new center's distances
```

`np.minimum` is elementwise (not `np.min`, which reduces to one number). After this line, `D2[c]` is 0, and so is every duplicate of `X[c]`, so none of them can be drawn again.

## 8. Full solution

```python
import numpy as np  # cumsum and searchsorted turn a weighted draw into a lookup


# Pick k seed row indices of X (n, d), using the given uniforms u (k,) instead of an RNG
def kmeans_pp_init(X: np.ndarray, k: int, u: np.ndarray) -> np.ndarray:
    n = X.shape[0]  # number of candidate points
    # first seed is uniform; the min is a defensive clamp in case u[0] == 1.0 is ever passed
    idx = [min(int(np.floor(u[0] * n)), n - 1)]
    D2 = np.sum((X - X[idx[0]]) ** 2, axis=1)  # (n,) squared distance to the nearest chosen center so far
    for j in range(1, k):  # draw each remaining seed in order
        cum = np.cumsum(D2)  # (n,) cumulative weights S; non-decreasing, so searchsorted works
        # first index with S > u[j] * total; side="right" makes it strict, so zero-weight points are never picked
        c = int(np.searchsorted(cum, u[j] * cum[-1], side="right"))
        idx.append(c)  # record the new seed in draw order
        D2 = np.minimum(D2, np.sum((X - X[c]) ** 2, axis=1))  # (n,) a new center can only shrink distances
    return np.array(idx, dtype=np.int64)  # (k,) chosen indices, in the order they were chosen
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[0, 2]` | the basic draw: $S = [0, 1, 10]$, $\tau = 5$ |
| Example 2 | `[2, 0, 3]` | the running minimum shrinks `D2[1]` from 5 to 1 |
| single center | `[58]` | `k = 1`: only $\lfloor u_0 n \rfloor$, no weighted draw |
| four blobs | `[62, 74, 38, 52]` | squared weights and the nearest-center minimum on real clusters |
| u zero after first center | `[0, 1, 2]` | $\tau = 0$ must skip zero-weight points (`side="right"`) |
| target on a boundary | `[0, 2]` | $\tau$ equals $S_1$ exactly; strict `>` moves past it |
| duplicate points | `[1, 4, 2]` | a duplicate of a chosen center has $D^2 = 0$ and can't be picked |
| k equals distinct count | `[3, 0, 2, 1]` | every point gets chosen; the running minimum must zero out each one |
| 5d many centers | 10 indices | `k = 10` in 5-D, every rule at once |

## 10. Complexity

With `n` points, `d` features and `k` seeds:

- **Time:** $O(knd)$. Each draw is one $O(nd)$ distance update, an $O(n)$ cumulative sum, and an $O(\log n)$ binary search.
- **Memory:** $O(n)$ for `D2` and `cum`, plus $O(nd)$ for the temporary difference.

Without the running minimum you'd recompute distances to all `j` chosen centers at step `j`, for $O(k^2 nd)$ total. At scale, k-means++ is inherently sequential (`k` passes over the data). For very large `n` and `k`, k-means|| (scalable k-means++) samples many seeds per pass and needs only a few passes. That's what Spark MLlib uses.

## 11. If you got Wrong Answer

- **"u zero after first center" and "target on a boundary" fail.** You used the default `side="left"` (`wrong_side_left.py`). It returns the first index with $S_i \ge \tau$, so with $\tau = 0$ it re-picks index 0, a center you already chose.
- **"four blobs", "target on a boundary" and "5d many centers" fail.** Your weights are distances, not squared distances (`wrong_distance_not_squared.py`). On "target on a boundary", plain distances give $S = [0, 1, 3, 6]$ and $\tau = 6/14 \approx 0.43$, so the draw lands on index 1 instead of 2.
- **Several multi-seed cases fail, but `k = 2` cases pass.** You compute $D^2$ to the most recent center only (`wrong_last_center_only.py`). With two seeds "newest" and "nearest" are the same; from the third seed on they differ. On "u zero after first center" this re-picks index 0 at the third draw.
- **Your first seed is off by one.** You rounded instead of flooring (`round(u[0] * n)`). The spec is $\lfloor u_0 n \rfloor$; `int()` or `np.floor` both truncate toward zero for these non-negative values.
- **You get the right set of indices in the wrong order.** Return them in draw order; don't sort them.

## 12. Follow-ups an interviewer might ask

- *Why not pick the farthest point every time?* That's farthest-first traversal. It's deterministic and grabs outliers, since an outlier is always the farthest point. Sampling in proportion to $D^2$ favors far regions but rarely picks a lone outlier, because one point has little total weight compared to a dense distant cluster.
- *How does this plug into k-means?* `kmeans(X, X[kmeans_pp_init(X, k, u)], max_iter)` from problem 17 (k-means). scikit-learn's default `init="k-means++"` also tries a few candidates per step and keeps the one that lowers cost most.
- *How would you sample with a real RNG?* `rng.choice(n, p=D2 / D2.sum())` does the same draw. The `u` interface just makes the result testable.
- *Does this help the Gaussian mixture?* Yes. EM is also sensitive to initialization, and k-means++ seeds are a common starting point for the means (problem 24, gmm-em).
- *Where else does inverse-CDF sampling show up?* Token sampling from a softmax in language models: cumulative probabilities plus one uniform, the same `searchsorted` lookup, with top-p truncation applied first.
