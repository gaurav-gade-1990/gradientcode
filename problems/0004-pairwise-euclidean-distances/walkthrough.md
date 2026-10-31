## 1. What the problem is really asking

You need the distance from every row of `A` to every row of `B`: an `(n, m)` grid. This is the inner loop of k-nearest neighbours (problem 16) and k-means (problem 17), so it runs constantly and has to be fast.

The definition suggests a double loop over pairs. That is `n * m` small operations in Python, and the hidden case with `n = m = 1000` makes it time out. The problem is really asking you to **turn a pairwise computation into one matrix product** by expanding the square, and then to deal with the one numerical wart that expansion introduces: rounding can make a squared distance slightly negative, and `np.sqrt` of a negative number is `nan`.

The judge compares the full matrix for small cases. For the timed case, `driver.py` builds `A` and `B` from a seed and compares a summary instead: the shape, the row and column sums, a strided sample `D[::97, ::89]`, and whether anything is `nan`. Tolerance is `rtol=1e-6`, `atol=1e-5`.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `A` | float array, shape `(n, d)` | one point per row |
| `B` | float array, shape `(m, d)` | one point per row, same `d` |
| return | float array, shape `(n, m)` | `D[i, j]` is the distance from `A[i]` to `B[j]` |

Details that are easy to miss:

- **Return distances, not squared distances.** Squared distances rank neighbours the same way, but the judge checks the values.
- **Equal points appear on purpose.** "A equals B (rounding goes negative)" passes the same matrix twice, and "duplicate rows" repeats rows across `A` and `B`. Those are the entries where rounding bites.
- **`atol = 1e-5`.** The tolerance is loose enough to absorb the leftover rounding noise on equal points after clipping. You don't need exact zeros on the diagonal.

## 3. The math

For row vectors $a, b \in \mathbb{R}^d$,

$$
\lVert a - b \rVert^2 = \sum_{k=1}^{d} (a_k - b_k)^2 = \sum_k a_k^2 - 2\sum_k a_k b_k + \sum_k b_k^2 = \lVert a \rVert^2 - 2\, a \cdot b + \lVert b \rVert^2 .
$$

Now do it for every pair at once. Let $A \in \mathbb{R}^{n \times d}$ and $B \in \mathbb{R}^{m \times d}$, and define

- $\alpha \in \mathbb{R}^{n \times 1}$ with $\alpha_i = \lVert a_i \rVert^2$ (a column),
- $\beta \in \mathbb{R}^{1 \times m}$ with $\beta_j = \lVert b_j \rVert^2$ (a row),
- $G = A B^\top \in \mathbb{R}^{n \times m}$ with $G_{ij} = a_i \cdot b_j$ (the cross terms, one matmul).

Then

$$
D^2 = \alpha \mathbf{1}_m^\top - 2G + \mathbf{1}_n \beta^\top,
\qquad D_{ij} = \sqrt{\max(D^2_{ij},\, 0)} .
$$

The $\alpha \mathbf{1}^\top$ and $\mathbf{1}\beta^\top$ terms are just "repeat the column across $m$ columns" and "repeat the row down $n$ rows". In NumPy that's broadcasting an `(n, 1)` against a `(1, m)`, with no copies made.

**Why rounding goes negative.** When $a_i = b_j$, the exact value is $\lVert a \rVert^2 - 2\lVert a \rVert^2 + \lVert a \rVert^2 = 0$. In floating point each of those three terms carries a relative error near machine epsilon $\varepsilon \approx 2.2 \times 10^{-16}$, so the result is $0 \pm$ roughly $\varepsilon \lVert a \rVert^2$. That's **catastrophic cancellation**: subtracting large, nearly equal numbers leaves only noise. Half the time the noise is negative. Clipping at 0 removes the `nan`; the leftover error after the square root is about $\sqrt{\varepsilon}\,\lVert a \rVert$, around $10^{-7}$ here, well under `atol`.

**The gradient.** k-means and metric learning move points to reduce distances, so you'll meet this. With $D = \lVert a - b \rVert = \big(\sum_k (a_k - b_k)^2\big)^{1/2}$, the chain rule gives

$$
\frac{\partial D}{\partial a_k} = \frac{1}{2D} \cdot 2(a_k - b_k) = \frac{a_k - b_k}{D},
\qquad \nabla_a D = \frac{a - b}{\lVert a - b \rVert} .
$$

A unit vector pointing from $b$ to $a$, undefined at $D = 0$. The squared distance has the friendlier gradient $\nabla_a D^2 = 2(a - b)$, which is one reason losses use $D^2$.

## 4. Trace an example by hand

**Example 1:** `A = [[0, 0], [3, 4]]` (shape `(2, 2)`), `B = [[0, 0], [6, 8], [3, 0]]` (shape `(3, 2)`).

```python
aa = np.sum(A * A, axis=1)[:, None]   # [[0], [25]]                  (2, 1)
bb = np.sum(B * B, axis=1)[None, :]   # [[0, 100, 9]]                (1, 3)
A @ B.T                               # [[0, 0, 0], [0, 50, 9]]      (2, 3)
d2 = aa - 2 * (A @ B.T) + bb          # [[0, 100, 9], [25, 25, 16]]  (2, 3)
np.sqrt(np.maximum(d2, 0))            # [[0, 10, 3], [5, 5, 4]]      (2, 3)
```

Check one entry by hand: `[3, 4]` to `[6, 8]` is `25 - 2*50 + 100 = 25`, and `sqrt(25) = 5`. That matches the problem's explanation.

**The hidden case that teaches the most, "A equals B (rounding goes negative)":** `A` and `B` are the same `(20, 8)` matrix, so the exact diagonal is all zeros. Running the expansion on it gives a minimum `d2` of `-1.78e-15`, and two entries come out negative. Without the clip, those two become `nan`, and the judge reports `output[6, 6]: expected 0, got nan`. With the clip, the largest leftover on a true-zero entry is `4.2e-8`, inside `atol`. In "duplicate rows" the worst `d2` is `-1.42e-14`, because those rows are scaled by 3 and the noise scales with $\lVert a \rVert^2$.

## 5. Key idea: column plus row broadcasts to a grid

The trick that makes this fast is that `(n, 1) + (1, m)` gives `(n, m)`. Broadcasting stretches each size-1 axis to match the other operand. So:

- `aa` must be a **column**, `(n, 1)`: `[:, None]` adds the axis.
- `bb` must be a **row**, `(1, m)`: `[None, :]`.

If you leave both as 1-D, `aa - 2*(A @ B.T)` aligns the `(n,)` with the **last** axis of `(n, m)`, which is `m`. When `n != m` you get "operands could not be broadcast together". When `n == m` (as in "A equals B" and the timed case) it silently adds row norms along the wrong axis and every off-diagonal value is wrong. When `n = 1` (Example 2, "single pair") it happens to work. That mix of crashes, silent errors and lucky passes is exactly what makes shape bugs hard to spot, so write the shape next to each line.

## 6. Plan before you code

```
aa = squared norm of each row of A, as a column      # (n, 1)
bb = squared norm of each row of B, as a row         # (1, m)
d2 = aa - 2 * (A @ B.T) + bb                         # (n, m)
return sqrt(max(d2, 0))                              # clip rounding noise, then root
```

| approach | time on 1000 x 1000 x 32 | extra memory |
|---|---|---|
| double Python loop | Time Limit Exceeded | none |
| `A[:, None, :] - B[None, :, :]`, then sum | passes (about 130 ms locally) | an `(n, m, d)` temporary: 256 MB |
| expand the square, one matmul | about 3 ms locally | `(n, m)` only |

## 7. Build it one piece at a time

**Step 1: the squared norms, shaped for broadcasting.**

```python
aa = np.sum(A * A, axis=1)[:, None]   # (n, d) -> (n,) -> (n, 1)
bb = np.sum(B * B, axis=1)[None, :]   # (m, d) -> (m,) -> (1, m)
```

`A * A` is elementwise squaring, and summing along `axis=1` adds over features, giving one number per point.

**Step 2: the cross terms and the squared distances.**

```python
d2 = aa - 2.0 * (A @ B.T) + bb        # (n, 1) - (n, m) + (1, m) -> (n, m)
```

`A @ B.T` is `(n, d) @ (d, m)`. All `n * m * d` multiply-adds happen inside BLAS.

**Step 3: clip, then take the root.**

```python
return np.sqrt(np.maximum(d2, 0.0))   # (n, m); no negatives, so no nan
```

`np.maximum` is elementwise (unlike `np.max`, which reduces). Use it rather than `np.abs`: both pass here, but `abs` turns `-1e-14` into `+1e-14`, which only looks more principled. The true value is 0, and clipping says so.

## 8. Full solution

```python
# NumPy gives elementwise ops, broadcasting and a BLAS-backed matrix product
import numpy as np


# A: (n, d), B: (m, d); returns the (n, m) matrix of Euclidean distances
def pairwise_distances(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    # squared length of each row of A, reshaped to a column (n, 1) so it repeats across columns
    aa = np.sum(A * A, axis=1)[:, None]
    # squared length of each row of B, reshaped to a row (1, m) so it repeats down rows
    bb = np.sum(B * B, axis=1)[None, :]
    # ||a||^2 - 2 a.b + ||b||^2 for every pair; one matmul gives all cross terms, (n, m)
    d2 = aa - 2.0 * (A @ B.T) + bb
    # rounding can leave equal points at -1e-15, so clip to 0 before the root to avoid nan
    return np.sqrt(np.maximum(d2, 0.0))
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `[[0, 10, 3], [5, 5, 4]]` | the expansion and the column-plus-row broadcast |
| Example 2 | `[[0, 3]]` | a point is 0 from itself; `‖[1, 2, 2]‖ = 3` |
| A equals B (rounding goes negative) | `0` on the diagonal | the clip: without it, `output[6, 6]` is `nan` |
| duplicate rows | `0` wherever rows match, e.g. `output[5, 2]` | the clip with larger norms, so larger noise |
| one dimension | `[[1, 4], [2, 7], [5, 0]]` | `d = 1`: distance is `|a - b|` |
| single pair | `[[4]]` | `n = m = 1`; `sqrt(4 * 2^2) = 4` |
| random rectangular, wide features | shapes `(9, 13)` and `(12, 10)` | `n != m` and `d` up to 64 |
| large (1000 x 1000, timed) | shape `(1000, 1000)`, first row sum `7853.6752`, `has_nan: False` | speed: a Python double loop times out |

## 10. Complexity

- **Time:** $O(nmd)$ for the matrix product, plus $O((n + m)d)$ for the norms and $O(nm)$ for the additions, clip and root. The product dominates, and BLAS runs it at close to peak FLOPs.
- **Memory:** $O(nm)$ for `d2` and the output. Nothing of size $nmd$ is built.

At scale, the `(n, m)` matrix is the limit: 100k by 100k float64 is 80 GB. You'd compute it in row blocks, keep only what you need from each block (the k nearest, or the argmin for k-means), and discard the rest. This is also why GPU k-means and FAISS use exactly this expansion: it turns distance computation into GEMM, the operation hardware is best at.

## 11. If you got Wrong Answer

- **`nan` at `output[6, 6]` in "A equals B" or at `output[5, 2]` in "duplicate rows".** You took `np.sqrt` without clipping (`wrong_no_clip.py`). Every other case passes, which is why it's easy to miss.
- **Values are the squares of the expected ones (`100` instead of `10`).** You returned squared distances (`wrong_squared.py`).
- **Time Limit Exceeded on "large (1000 x 1000, timed)" only.** You looped over pairs (`wrong_double_loop.py`). Every small case passes.
- **Runtime Error "operands could not be broadcast together with shapes (2,) (2,3)", but Example 2 passes.** Your norms are 1-D. Add `[:, None]` and `[None, :]`. On square inputs this gives wrong values instead of an error.
- **Off-diagonal values wrong only on square inputs.** Same bug: `aa` was added along the wrong axis.

## 12. Follow-ups an interviewer might ask

- *How do you find the k nearest neighbours from this?* `np.argpartition(D, k, axis=1)[:, :k]`, then sort those k. You can even skip the square root, since it doesn't change the order (problem 16, k-nearest-neighbors).
- *How do you get exact zeros for identical points?* You can't with this formula. If it matters, recompute the few smallest distances directly as `‖a - b‖`, which is what some libraries do for the final top-k.
- *How is this used in k-means?* Each iteration computes the `(n, k)` distances from points to centroids and takes the argmin per row (problem 17, k-means). The $\lVert a \rVert^2$ term is constant per row, so the argmin needs only $-2G + \beta$.
- *How does this relate to cosine similarity?* For unit vectors, $\lVert a - b \rVert^2 = 2 - 2\cos(a, b)$ (problem 3, cosine-similarity-matrix).
- *What about float32 on a GPU?* $\varepsilon$ is $1.2 \times 10^{-7}$, so the noise on equal points is around $\sqrt{\varepsilon}\lVert a \rVert \approx 10^{-3}\lVert a \rVert$. Clipping is mandatory, and small distances are unreliable; center the data first to shrink the norms.
