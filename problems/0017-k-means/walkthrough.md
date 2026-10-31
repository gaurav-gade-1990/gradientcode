## 1. What the problem is really asking

k-means groups `n` points into `k` clusters, each represented by a centroid. Lloyd's algorithm finds those centroids by alternating two steps until nothing moves:

> **assign** every point to its nearest centroid, then **update** every centroid to the mean of its points.

Under the story, this is a **fixed-point iteration** built from two vectorized pieces you already know: a pairwise distance matrix with an `argmin` (problem 16, k-nearest-neighbors, uses the same broadcast), and a group-by mean.

The judge checks both outputs: the `(k, d)` centroids within `rtol = 1e-7`, and the `(n,)` labels exactly. Because the start is given (`init_centroids`), there's no randomness. Every run has one correct answer, and four rules pin it down: the lowest-index tie rule, the empty-cluster rule, the exact-equality stop, and the requirement that labels match the centroids you return.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `X` | `(n, d)` | the points | fixed for the whole run |
| `init_centroids` | `(k, d)` | the starting centroids | copied into `C`, never modified in place |
| `max_iter` | int, `0..100` | the most assign/update rounds | the loop bound |
| return | `((k, d), (n,))` | final centroids and labels | labels are recomputed against the returned centroids |

Three details are easy to miss:

- **`max_iter = 0` is legal.** The loop body never runs, but you still have to return labels. If your labels only exist inside the loop, you get `NameError` (a Runtime Error on the "zero iterations" case).
- **A cluster can be empty.** Example 2 puts a centroid at `(100, 100)`, far from every point. The mean of zero points is `nan`, and the spec says to keep the old value instead.
- **Labels must match the returned centroids.** When `max_iter` runs out, the labels from the last assign step were computed against the centroids *before* the last update. You need one more assign.

## 3. The math

Let $c_1, \dots, c_k \in \mathbb{R}^d$ be the centroids and $\ell_i \in \{1..k\}$ the label of point $x_i$. k-means minimizes the within-cluster sum of squares:

$$
J(\ell, c) = \sum_{i=1}^{n} \lVert x_i - c_{\ell_i} \rVert^2 .
$$

Lloyd's algorithm is coordinate descent on $J$: fix one set of variables, minimize over the other, repeat.

**Assign step (fix $c$, minimize over $\ell$).** Each term depends on one $\ell_i$ only, so each point independently picks the centroid that makes its term smallest:

$$
\ell_i = \arg\min_{j} \lVert x_i - c_j \rVert^2 .
$$

**Update step (fix $\ell$, minimize over $c$).** Let $S_j = \{ i : \ell_i = j \}$. The part of $J$ that depends on $c_j$ is $J_j(c_j) = \sum_{i \in S_j} \lVert x_i - c_j \rVert^2$. Expand one term: $\lVert x_i - c_j\rVert^2 = (x_i - c_j)^\top (x_i - c_j)$. Its gradient with respect to $c_j$ is $-2(x_i - c_j)$. Summing and setting to zero:

$$
\nabla_{c_j} J_j = -2 \sum_{i \in S_j} (x_i - c_j) = 0
\;\;\Longrightarrow\;\;
|S_j|\, c_j = \sum_{i \in S_j} x_i
\;\;\Longrightarrow\;\;
c_j = \frac{1}{|S_j|} \sum_{i \in S_j} x_i .
$$

The Hessian is $2|S_j| I$, positive definite, so this is the minimum: the mean. When $|S_j| = 0$, $J_j$ doesn't depend on $c_j$ at all and the formula divides by zero. Any value is "optimal", and the spec picks "keep the current one".

Since neither step can increase $J$ and there are finitely many labelings, the algorithm reaches a point where the update reproduces the same centroids. That's the stop condition. It is a local minimum, not necessarily the global one; the starting point decides which (problem 18, k-means-plus-plus-init).

## 4. Trace an example by hand

**Example 1.** `X` is `(6, 1)`: `0, 1, 2, 10, 11, 12`. `C` starts as `[[0], [2]]`, shape `(2, 1)`.

The first distance matrix `D` has shape `(6, 2)`:

| point | $D$ to $c_0 = 0$ | $D$ to $c_1 = 2$ | label |
|---|---|---|---|
| 0 | 0 | 4 | 0 |
| 1 | 1 | 1 | **0** (tie, lowest index) |
| 2 | 4 | 0 | 1 |
| 10 | 100 | 64 | 1 |
| 11 | 121 | 81 | 1 |
| 12 | 144 | 100 | 1 |

| iteration | labels | new centroids | equal to `C`? |
|---|---|---|---|
| 1 | `[0, 0, 1, 1, 1, 1]` | `[0.5, 8.75]` | no |
| 2 | `[0, 0, 0, 1, 1, 1]` | `[1, 11]` | no |
| 3 | `[0, 0, 0, 1, 1, 1]` | `[1, 11]` | **yes, stop** |

The output is centroids `[[1], [11]]` and labels `[0, 0, 0, 1, 1, 1]`.

**Example 2** is the empty-cluster case, with `max_iter = 1`. The initial distances from the four points to `c_1 = (100, 100)` are around 19,000 to 20,000, against 0.25 to 16.25 for `c_0 = (0, 0.5)`. All four points go to cluster 0, which moves to their mean `(2, 0.5)`. Cluster 1 has no points and keeps `(100, 100)`. The loop has used its one iteration, so you assign once more against `[[2, 0.5], [100, 100]]` and get labels `[0, 0, 0, 0]`.

If you replace the empty cluster's centroid with `nan`, the returned centroid is `[nan, nan]`, and the labels come out `[1, 1, 1, 1]`: every distance to that centroid is `nan`, and `np.argmin` treats `nan` as the minimum. One empty cluster swallows every point.

## 5. Key idea: `argmin` already implements the tie rule

`np.argmin(D, axis=1)` returns, for each row, the index of the **first** occurrence of the smallest value. "First" is "lowest centroid index", which is exactly the spec. The hidden "assignment ties" case leans on this: the point `(1, 0)` has squared distance 1 to both centroid 0 at `(2, 0)` and centroid 2 at `(0, 0)`, and must go to 0. The expected labels are `[0, 1, 2, 2, 0, 1]`.

Compare this with problem 16, where the tie rule needed `kind="stable"`. There you sorted; here you only need the minimum, and `argmin` is deterministic.

## 6. Plan before you code

```
C = float copy of init_centroids                     # (k, d)
repeat max_iter times:
    labels = argmin over centroids of squared distance # (n,)
    new = copy of C                                  # empty clusters keep their value
    for each cluster j with at least one point:
        new[j] = mean of its points
    if new is exactly C: stop
    C = new
labels = assign against C one final time
return C, labels
```

| situation | what `new[j]` is |
|---|---|
| cluster `j` has points | their mean |
| cluster `j` is empty | `C[j]` unchanged (comes from `C.copy()`) |

## 7. Build it one piece at a time

**Step 1: the assign step as a helper.** You call it inside the loop and once at the end, so write it once.

```python
def assign(X, C):
    diff = X[:, None, :] - C[None, :, :]                       # (n, 1, d) - (1, k, d) -> (n, k, d)
    return np.argmin(np.sum(diff * diff, axis=-1), axis=1)     # (n, k) -> (n,)
```

The broadcast is the same as in k-NN: inserting `None` makes a length-1 axis that stretches to match. Summing over the last axis gives one squared distance per (point, centroid) pair.

**Step 2: copy the start as floats.**

```python
C = np.array(init_centroids, dtype=float)                      # (k, d), a new array
```

`np.array` copies, so you never modify the caller's array. `dtype=float` matters if someone passes integer centroids: assigning a mean like `0.5` into an integer array silently truncates it to `0`.

**Step 3: the update, starting from a copy.**

```python
new = C.copy()                                                 # (k, d)
for j in range(k):
    members = X[labels == j]                                   # (|S_j|, d), boolean mask
    if len(members) > 0:
        new[j] = members.mean(axis=0)                          # (d,)
```

Starting from `C.copy()` makes the empty-cluster rule automatic: a cluster you skip keeps its value. `labels == j` is an `(n,)` boolean mask, and `X[mask]` keeps the rows where it's `True`. `mean(axis=0)` averages down the rows, giving a `(d,)` vector.

**Step 4: stop on exact equality, then relabel.**

```python
if np.array_equal(new, C):
    break
C = new
...
return C, assign(X, C)
```

`np.array_equal` checks every value is identical. A tolerance would also stop, but the spec says exactly equal, and the means reproduce bit-for-bit once the labels stop changing (same points, same order, same sum). The final `assign` is cheap and covers three cases at once: `max_iter = 0`, running out of iterations, and converging (where it returns the same labels as the last loop pass).

## 8. Full solution

```python
import numpy as np  # broadcasting for distances, boolean masks for the group means


# Nearest-centroid labels: X (n, d), C (k, d) -> (n,)
def assign(X, C):
    diff = X[:, None, :] - C[None, :, :]  # (n, k, d): every point minus every centroid
    # (n, k) squared distances -> (n,); argmin's first-minimum rule gives the lowest index on ties
    return np.argmin(np.sum(diff * diff, axis=-1), axis=1)


# Lloyd's algorithm from fixed starting centroids; returns ((k, d) centroids, (n,) labels)
def kmeans(X: np.ndarray, init_centroids: np.ndarray, max_iter: int) -> tuple:
    C = np.array(init_centroids, dtype=float)  # (k, d) float copy, so means aren't truncated or written back
    k = C.shape[0]  # number of clusters
    for _ in range(max_iter):  # at most max_iter assign/update rounds
        labels = assign(X, C)  # (n,) assign step against the current centroids
        new = C.copy()  # (k, d) start from C so an empty cluster keeps its current value
        for j in range(k):  # update each centroid from its own points
            members = X[labels == j]  # (|S_j|, d) points currently labeled j
            if len(members) > 0:  # the mean of zero points is nan, so only update non-empty clusters
                new[j] = members.mean(axis=0)  # (d,) the mean minimizes this cluster's squared error
        if np.array_equal(new, C):  # nothing moved: we've reached the fixed point
            break  # stop early as the spec requires
        C = new  # accept the update and go round again
    return C, assign(X, C)  # relabel against the returned centroids (covers max_iter = 0 and running out)
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[[1], [11]]`, labels `[0, 0, 0, 1, 1, 1]` | the basic loop, a tie at `x = 1`, and the stop after iteration 3 |
| Example 2 | `[[2, 0.5], [100, 100]]`, labels `[0, 0, 0, 0]` | the empty cluster keeps its centroid; relabel after the last iteration |
| zero iterations | the initial centroids | `max_iter = 0` still returns labels |
| three blobs converge | converges at iteration 5 | the ordinary case; early stop well before 100 |
| stops at max_iter | 2 iterations (it would need 28 to converge) | labels come from a final assign; stale labels differ on 24 of 300 points |
| empty cluster persists | 4th centroid stays `[-50, -50]` | a cluster that's empty on every iteration |
| assignment ties | labels `[0, 1, 2, 2, 0, 1]` | the lowest-index tie rule from `argmin` |
| single cluster | one centroid at the mean of the 50 points | `k = 1`, a start far from the data |
| many clusters 4d | converges at iteration 14 | `k = 8` in 4-D, where the distance metric matters |

## 10. Complexity

With `T` iterations, `n` points, `k` clusters and `d` features:

- **Time:** $O(T\,nkd)$ for the distances. The update builds `k` masks over `n` labels ($O(T\,nk)$) and averages each point once ($O(T\,nd)$), so the distances dominate.
- **Memory:** $O(nkd)$ for the broadcast `diff`. At the limits that's $500 \cdot 10 \cdot 8 = 40{,}000$ floats, trivial here.

At scale (millions of points), two changes matter. Replace the broadcast with the expansion $\lVert x\rVert^2 - 2x^\top c + \lVert c\rVert^2$, a single matrix multiply with $O(nk)$ memory (problem 4, pairwise-euclidean-distances). Replace the per-cluster loop with `np.add.at(sums, labels, X)` and `np.bincount(labels, minlength=k)`, which compute all sums and counts in one pass. Mini-batch k-means goes further and updates from a random sample each step.

## 11. If you got Wrong Answer

- **Runtime Error on "zero iterations".** You return `labels` from inside the loop, and with `max_iter = 0` it was never assigned. Always assign after the loop.
- **"stops at max_iter" fails but everything else passes.** Your labels are stale: they were computed before the last update (`wrong_stale_labels.py`). When the loop converges, stale and fresh labels agree, which is why only this case catches it.
- **Example 2 shows `[nan, nan]` or `[0, 0]` for the second centroid.** You computed the mean of an empty set, or replaced it with zeros (`wrong_empty_cluster_nan.py` uses zeros). With `nan`, every label becomes `1`, because `argmin` treats `nan` as smallest. With zeros, the centroid jumps to the origin and steals points 0 and 1. Start `new` from `C.copy()` and skip empty clusters. "empty cluster persists" fails for the same reason.
- **"stops at max_iter" and "many clusters 4d" fail.** You're using L1 distance (`np.abs(...).sum(-1)`, `wrong_manhattan.py`). The mean minimizes squared L2 distance; L1 pairs with the median.
- **Centroids drift by tiny amounts.** Check you didn't cast `C` to an integer type, or compare with a tolerance that stops one iteration early.

## 12. Follow-ups an interviewer might ask

- *How do you choose the starting centroids?* Random points can land in the same cluster and converge to a bad local minimum. k-means++ spreads them out by sampling proportionally to squared distance (problem 18, k-means-plus-plus-init).
- *How do you choose `k`?* Plot $J$ against `k` and look for the elbow, or use the silhouette score. $J$ always drops as `k` grows, so you can't just minimize it.
- *What's the probabilistic version?* A Gaussian mixture fit by EM (problem 24, gmm-em). k-means is its limit with equal spherical covariances and hard assignments.
- *What would you do about an empty cluster in production?* Keeping the old value (as here) leaves a dead centroid. Libraries often re-seed it at the point farthest from its centroid, which tends to split the worst cluster.
- *Why standardize first?* Squared distance adds up feature differences, so a large-scale feature dominates the clustering (problem 7, standardize-features).
