## 1. What the problem is really asking

k-nearest neighbors has no training step. "Fitting" is just keeping `X_train` and `y_train`. All the work happens at prediction time:

> for each test point, find the `k` training points closest to it, and let them vote.

Under the story, this is three array operations in a row: a **pairwise distance matrix**, a **per-row sort**, and a **per-row vote**. The first two are pure NumPy. The vote has a custom tie rule, and that rule is what most of the hidden tests are about.

The judge compares your `(m,)` array of predicted labels to the reference **exactly** (`rtol = 0`, `atol = 0`). There is no partial credit for "almost the same neighbors". So you have to follow both tie rules to the letter: distance ties go to the lower training index, and vote ties go to the label of the nearest neighbor.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `X_train` | `(n, d)` | the stored training points | the right side of every distance |
| `y_train` | `(n,)` int | their labels, in `[0, 20)` | indexed by neighbor positions |
| `X_test` | `(m, d)` | the points to classify | one prediction per row |
| `k` | int, `1 <= k <= n` | how many neighbors vote | slice the sorted order to `[:, :k]` |
| return | `(m,)` int | one label per test row | compared exactly |

Three details are easy to miss:

- **The test points are not in the training set.** The nearest neighbor counts, even at distance 0. Slicing `[:, 1:k+1]` (the leave-one-out habit) is wrong here.
- **Distance ties are real, not theoretical.** Two tests use integer grids, where many training points sit at exactly the same distance from a test point. Which ones make the cut at position `k` depends on your tie rule.
- **Vote ties are not broken by the smallest label.** `np.bincount(row).argmax()` returns the smallest tied label. The rule here is "the tied label that appears first in the neighbor order", which is a different label whenever the nearest neighbor's label isn't the smallest.

## 3. The math

Let $x_i \in \mathbb{R}^d$ be test row $i$ and $t_j \in \mathbb{R}^d$ be training row $j$. The Euclidean distance is

$$
\operatorname{dist}(x_i, t_j) = \lVert x_i - t_j \rVert_2 = \sqrt{\sum_{c=1}^{d} (x_{ic} - t_{jc})^2 }.
$$

The square root is monotone increasing on $[0, \infty)$: if $a < b$ then $\sqrt a < \sqrt b$, and if $a = b$ then $\sqrt a = \sqrt b$. So sorting by squared distance gives exactly the same order, ties included. You can skip the root and work with

$$
D_{ij} = \sum_{c=1}^{d} (x_{ic} - t_{jc})^2, \qquad D \in \mathbb{R}^{m \times n}.
$$

Let $\pi_i(1), \dots, \pi_i(n)$ be the training indices sorted by $D_{ij}$ ascending, with ties broken by smaller $j$. The neighbor set is $N_i = (\pi_i(1), \dots, \pi_i(k))$. The vote count for label $c$ is

$$
v_i(c) = \sum_{r=1}^{k} \mathbb{1}\big[\, y_{\pi_i(r)} = c \,\big],
$$

and the prediction is the label at the smallest rank $r$ whose label has the top count:

$$
\hat y_i = y_{\pi_i(r^*)}, \qquad r^* = \min \{\, r : v_i(y_{\pi_i(r)}) = \max_c v_i(c) \,\}.
$$

There is no gradient here: k-NN has no parameters to learn. The only modelling choice is $k$. A small $k$ follows the training labels closely (low bias, high variance), a large $k$ smooths over them, and $k = n$ predicts the majority class everywhere, up to the tie rule.

## 4. Trace an example by hand

**Example 2** teaches the vote-tie rule. `X_train` is `(4, 2)`, `X_test` is `(1, 2)`, `k = 2`.

The broadcast difference `X_test[:, None, :] - X_train[None, :, :]` has shape `(1, 4, 2)`. Squaring and summing over the last axis gives `D` with shape `(1, 4)`:

| train index | point | label | $D$ from `(1, 0)` |
|---|---|---|---|
| 0 | `(0, 0)` | 2 | 1 |
| 1 | `(3, 0)` | 1 | 4 |
| 2 | `(0, 2)` | 1 | 5 |
| 3 | `(5, 5)` | 2 | 41 |

The stable argsort of that row is `[0, 1, 2, 3]`. The first `k = 2` are indices `0, 1`, so the neighbor labels are `[2, 1]`. `np.bincount([2, 1])` is `[0, 1, 1]`: labels 1 and 2 both have one vote. `argmax` would return `1`. Walking the neighbors from nearest to farthest, the first label with the top count is `2`, the label of the point at distance 1. The expected output is `[2]`.

**The hidden "grid distance ties" case** teaches the distance-tie rule. Take test row 1, the point `(2, 3)`, with `k = 4`. The seven nearest training points, in stable order:

| rank | train index | $D$ | label |
|---|---|---|---|
| 1 | 10 | 1 | 0 |
| 2 | 29 | 1 | 1 |
| 3 | 1 | 2 | 1 |
| 4 | 5 | 2 | 3 |
| 5 | 23 | 2 | 3 |
| 6 | 24 | 2 | 3 |
| 7 | 14 | 4 | 0 |

Four training points tie at $D = 2$, and only two of them fit in `k = 4`. With the lower-index rule the neighbors are `10, 29, 1, 5` with labels `[0, 1, 1, 3]`, and label `1` wins with two votes. If you broke ties by the higher index you'd take `29, 10, 24, 23` with labels `[1, 0, 3, 3]`, and label `3` would win. The reference output for this row is `1`; `wrong_index_tie_reversed.py` gives `3`.

## 5. Key idea: a stable sort encodes the distance-tie rule for free

`np.argsort(D, axis=1, kind="stable")` sorts each row by value. "Stable" means that equal values keep their original relative order. The original order of a row of `D` is the training index order, so equal distances come out lowest index first. That is the problem's rule, with no extra code.

The default `kind="quicksort"` makes no such promise. A version identical to the solution except for the missing `kind="stable"` passes eight of the nine cases and fails **grid distance ties**. On random float data exact ties almost never happen, which is why the bug hides until the grid test.

You could also use `np.lexsort((np.arange(n), D_row))` to sort by distance and then by index, but stable `argsort` says the same thing in one call.

## 6. Plan before you code

```
D  = squared distances, shape (m, n)
nn = stable argsort of each row, first k columns      # (m, k), nearest first
labels = y_train[nn]                                  # (m, k)
for each row of labels:
    counts = votes per label
    top = the highest count
    answer = first label in the row whose count == top
return answers as an int array of shape (m,)
```

The two tie rules map to two lines:

| rule | where it lives |
|---|---|
| equal distance: lower training index first | `kind="stable"` in the argsort |
| equal votes: nearest neighbor's label wins | scanning `row` left to right for the first label with `counts[lab] == top` |

## 7. Build it one piece at a time

**Step 1: the distance matrix by broadcasting.**

```python
diff = X_test[:, None, :] - X_train[None, :, :]   # (m, 1, d) - (1, n, d) -> (m, n, d)
D = np.sum(diff * diff, axis=-1)                  # (m, n)
```

`X_test[:, None, :]` inserts a length-1 axis in the middle, and `X_train[None, :, :]` inserts one at the front. Broadcasting stretches each length-1 axis to match the other array, so `diff[i, j]` is `X_test[i] - X_train[j]`. Summing the squares over the last axis (the `d` features) leaves one number per (test, train) pair. Using `diff * diff` instead of `np.linalg.norm` skips the square root, which section 3 showed doesn't change the order.

**Step 2: sort each row and keep the first `k`.**

```python
nn = np.argsort(D, axis=1, kind="stable")[:, :k]  # (m, k) training indices, nearest first
labels = y_train[nn]                              # (m, k) their labels
```

`axis=1` sorts within each test row, not down the columns. `y_train[nn]` is fancy indexing: an integer array used as an index returns an array of the same shape `(m, k)`, filled with the labels at those positions.

**Step 3: vote with the custom tie rule.**

```python
preds = np.empty(len(X_test), dtype=np.int64)     # (m,)
for i, row in enumerate(labels):                  # row: (k,)
    counts = np.bincount(row)                     # (max(row) + 1,)
    top = counts.max()
    for lab in row:
        if counts[lab] == top:
            preds[i] = lab
            break
```

`np.bincount(row)` returns an array where position `c` holds how many times `c` appears in `row`. Labels are small non-negative integers (under 20), so this is a cheap histogram. The inner loop walks `row` in neighbor order, so the first label that reaches `top` is the nearest one among the tied labels. The loop over test rows is a Python loop, but it runs `m <= 300` times over rows of length `k`, which is nothing next to the distance step.

## 8. Full solution

```python
import numpy as np  # broadcasting, argsort and bincount do all the heavy lifting


# X_train (n, d), y_train (n,), X_test (m, d) -> predicted labels (m,)
def knn_predict(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, k: int) -> np.ndarray:
    diff = X_test[:, None, :] - X_train[None, :, :]  # (m, n, d): every test row minus every train row
    D = np.sum(diff * diff, axis=-1)  # (m, n) squared distances; skipping sqrt keeps the same order
    nn = np.argsort(D, axis=1, kind="stable")[:, :k]  # (m, k) nearest first; stable = lower index wins ties
    labels = y_train[nn]  # (m, k) the neighbors' labels, still nearest first
    preds = np.empty(len(X_test), dtype=np.int64)  # (m,) one integer label per test row
    for i, row in enumerate(labels):  # vote separately for each test point; row is (k,)
        counts = np.bincount(row)  # votes per label: counts[c] = how many neighbors have label c
        top = counts.max()  # the winning vote count, possibly shared by several labels
        for lab in row:  # walk neighbors nearest to farthest so the nearest tied label is found first
            if counts[lab] == top:  # this label is one of the tied winners
                preds[i] = lab  # nearest tied label wins the vote tie
                break  # stop at the first winner; later tied labels must not overwrite it
    return preds  # (m,) predicted labels
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[0, 1]` | the basic pipeline in 1-D: distances, sort, majority of 3 |
| Example 2 | `[2]` | a 1-1 vote tie goes to the nearest neighbor's label, not the smaller label |
| k equals 1 | 25 labels | the nearest neighbor alone decides; catches skipping the nearest |
| three blobs k=5 | 25 labels | ordinary majority voting on three Gaussian clusters |
| even k ties | 25 labels | with `k = 4`, 2-2 ties happen and need the nearest-label rule |
| grid distance ties | 20 labels | exact distance ties at the `k` boundary need `kind="stable"` |
| distance tie at boundary | `[3]` | `x = 1` and `x = -1` are both at distance 1 from 0; the lower index (label 3) wins |
| k equals n | 20 labels | every point votes; label counts `[2, 2, 2, 1]` tie three ways, so only the tie rule decides |
| larger | 60 labels | 10 classes in 6-D; many ways for the vote to tie |

The "k equals n" case is worth a look. The seven training labels are `[2, 0, 1, 0, 2, 1, 3]`, so labels 0, 1 and 2 have two votes each for **every** test point. The prediction is whichever of them belongs to the nearest training point, which is why the expected output is a mix of 1s and 2s, and why `argmax` returns all zeros.

## 10. Complexity

With `m` test rows, `n` training rows and `d` features:

- **Distances:** $O(mnd)$ time and $O(mnd)$ memory for the broadcast `diff`. At the limits that's $300 \cdot 300 \cdot 10 = 900{,}000$ floats, about 7 MB.
- **Sort:** $O(mn \log n)$.
- **Vote:** $O(mk)$.

At production scale (millions of training points) you can't sort every row. Two changes help. First, the expansion $\lVert x - t\rVert^2 = \lVert x\rVert^2 - 2\,x\cdot t + \lVert t\rVert^2$ turns the distance step into one matrix multiply with $O(mn)$ memory, as in problem 4 (pairwise-euclidean-distances). It passes every test here, but on other data floating-point rounding can make two exactly-equal distances differ by a tiny amount and flip a tie. Second, `np.argpartition(D, k - 1, axis=1)` finds the `k` smallest in $O(n)$ per row, though it doesn't keep the stable tie order, so you'd re-sort just those `k` (problem 9, top-k-per-row). Beyond that, real systems use approximate nearest-neighbor indexes (HNSW, IVF) and accept a small recall loss.

## 11. If you got Wrong Answer

- **Every case fails, including Example 1.** You probably skipped the nearest neighbor with `[:, 1:k+1]` (`wrong_skip_nearest.py`). That's leave-one-out on the training set; here the test points are new.
- **Example 2 gives `[1]`.** You used `np.bincount(row).argmax()`, which breaks vote ties by the smallest label (`wrong_smallest_label_tiebreak.py`). It also fails "even k ties", "k equals n" (it returns all zeros) and "larger".
- **Only "grid distance ties" fails.** Your sort isn't stable. Add `kind="stable"`.
- **"distance tie at boundary" gives `[5]`.** You break distance ties by the higher index (`wrong_index_tie_reversed.py`), so `x = -1` (index 1, label 5) beat `x = 1` (index 0, label 3). The same bug fails the grid cases.
- **Shape errors in the distance step.** Check the `None` positions: `X_test[:, None, :]` is `(m, 1, d)` and `X_train[None, :, :]` is `(1, n, d)`. Swapping them gives `(n, m)` distances and sorts the wrong axis.

## 12. Follow-ups an interviewer might ask

- *How would you weight the votes?* Use distance weights, such as $1 / (D_{ij} + \varepsilon)$, and sum weights per label instead of counting. The $\varepsilon$ keeps a test point that exactly matches a training point from dividing by zero.
- *How do you choose `k`?* Cross-validation over a grid of `k` values (problem 31, stratified-k-fold). An odd `k` avoids 1-1 ties in binary problems, but not in multi-class ones.
- *Why does feature scaling matter here?* Euclidean distance adds squared differences across features, so a feature measured in thousands drowns out one measured in fractions. Standardize first (problem 7, standardize-features).
- *What happens in high dimensions?* Distances concentrate: the nearest and farthest points end up almost equally far, so "nearest" carries little information. Reduce dimension first, for example with PCA (problem 22).
- *How do you serve this over millions of points?* An approximate nearest-neighbor index, the same machinery a vector database uses for retrieval. The cosine-similarity version is problem 3 (cosine-similarity-matrix).
