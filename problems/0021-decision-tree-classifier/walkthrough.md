## 1. What the problem is really asking

A decision tree is problem 20 (gini-impurity-best-split) applied **recursively**. At the root you find the best split of all the training data. That cuts the data in two, and you do the same thing to each half, and so on, until a stopping rule says "this node is a leaf". To predict, a test point walks from the root down, going left or right at each split, and takes the label of the leaf it lands in.

Under the story, this is a **recursive build over subsets** plus a **tree walk**. The split search is code you've written before. The new parts are the four stopping rules, the leaf label, and making sure that training and prediction use exactly the same comparison.

The judge only sees your `(m,)` array of predictions, compared exactly. It never inspects the tree. But one wrong threshold deep in the tree, or one leaf that should have split, changes the label of any test point that reaches it. The hidden tests put test points exactly on thresholds and between training values to expose those differences.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `X_train` | `(n, d)` | training features | subset at every node |
| `y_train` | `(n,)` int, `0..9` | labels | split scores and leaf majorities |
| `X_test` | `(m, d)` | points to classify | each walks the finished tree |
| `max_depth` | int, `0..10` | the deepest level a node may be at | the root is depth 0 |
| `min_samples_split` | int, default 2 | the smallest node allowed to split | a node with fewer samples is a leaf |
| return | `(m,)` int | one prediction per test row | compared exactly |

Three details are easy to miss:

- **Depth counts from 0.** `max_depth = 0` means the root is a leaf: every test point gets the overall majority. `max_depth = 1` means one split and two leaves.
- **`min_samples_split` is "fewer than", not "at most".** A node with exactly `min_samples_split` samples may still split.
- **Thresholds are node-local.** Each node computes midpoints from the unique values of **its own** samples. A threshold from the root's values can make the same partition at a child but return a different number, and that number decides where unseen test points go.

## 3. The math

**The leaf label.** A leaf with label counts $n_c$ predicts $\hat y = \arg\max_c n_c$, ties to the smallest $c$. That's the label that minimizes the number of training mistakes in the leaf, $\sum_c n_c - n_{\hat y}$.

**The split criterion.** For a node with sample set $S$, the Gini impurity is $G(S) = 1 - \sum_c p_c^2$ (derived in problem 20 as the chance that two random draws disagree). A split into $L$ and $R$ scores

$$
\text{score}(j, t) = \frac{|L|}{|S|}\, G(L) + \frac{|R|}{|S|}\, G(R).
$$

The **impurity decrease** is $\Delta = G(S) - \text{score}(j, t)$. It's never negative, because $G$ is concave in the class fractions and the parent's fractions are the size-weighted average of the children's:

$$
p_c(S) = \frac{|L|}{|S|} p_c(L) + \frac{|R|}{|S|} p_c(R)
\quad\Longrightarrow\quad
G(S) \ge \frac{|L|}{|S|} G(L) + \frac{|R|}{|S|} G(R)
$$

by Jensen's inequality. Equality holds when the children have the same class fractions as the parent.

**Why greedy, and why split when $\Delta = 0$.** Finding the tree that minimizes total impurity under a size limit is NP-hard, so CART makes the locally best choice at each node and never revisits it. Greedy can be shortsighted: on XOR (Examples 2 and 3), every root split has $\Delta = 0$, because each child is still half and half. The spec says to split anyway. One level later, each child splits perfectly. A rule that demanded $\Delta > 0$ would stop at the root and miss that.

**The stopping rules.** A node at depth $\delta$ with samples $S$ is a leaf if:

| rule | why it exists |
|---|---|
| $\delta = $ `max_depth` | caps model complexity, the main guard against overfitting |
| $\lvert S\rvert <$ `min_samples_split` | don't fit tiny groups of samples |
| $S$ is pure | nothing left to separate; every split would score 0 anyway |
| no candidate threshold | every row in $S$ is identical, so no split can separate them |

## 4. Trace an example by hand

**Example 1.** `X_train` is `1..6` in one column, `y_train = [0, 0, 1, 1, 0, 0]`, `max_depth = 2`.

**Root (depth 0)**, six samples. The candidates are `1.5, 2.5, 3.5, 4.5, 5.5`. `2.5` and `4.5` both score `1/3`, and `2.5` comes first. Split: `x0 <= 2.5`.

- **Left (depth 1)**: `{1, 2}`, labels `[0, 0]`. Pure, so a leaf predicting `0`.
- **Right (depth 1)**: `{3, 4, 5, 6}`, labels `[1, 1, 0, 0]`. Its own midpoints are `3.5, 4.5, 5.5`, and `4.5` splits it into `[1, 1]` and `[0, 0]`. Split: `x0 <= 4.5`.
  - Both children are at depth 2, which equals `max_depth`, so they're leaves predicting `1` and `0`.

The tree:

```
x0 <= 2.5
  leaf 0
  x0 <= 4.5
    leaf 1
    leaf 0
```

| test point | path | prediction |
|---|---|---|
| 1.5 | `1.5 <= 2.5`, left | 0 |
| 3.5 | right, then `3.5 <= 4.5`, left | 1 |
| 5.5 | right, right | 0 |
| 2.5 | `2.5 <= 2.5`, **left** | 0 |

The last row is the routing trap. `2.5` sits exactly on the root threshold. With `x[j] <= t` it goes left and gets `0`; with `x[j] < t` it goes right, then left at `4.5`, and gets `1`. The expected output is `[0, 1, 0, 0]`.

**The hidden "node-local thresholds" case.** Seven training points; the root splits on `x1 <= 3.0`. The left child holds the four points with `x0` in `{0, 10}` and labels `0` at `x0 = 0`, `1` at `x0 = 10`. Its node-local midpoint is `(0 + 10) / 2 = 5.0`. The root's `x0` values are `{0, 4, 5, 6, 10}`, so a global candidate list would start with `2.0`, which makes the same partition of this child and comes first. The test points `(3.0, 0.5)` and `(4.5, 0.5)` fall between `2.0` and `5.0`: node-local thresholds send them left (label `0`), global ones send them right (label `1`). Expected: `[0, 0, 0, 1, 1, 1]`.

## 5. Key idea: represent the tree as nested tuples

You need a structure that holds either a label or a split with two subtrees. Two tuple shapes are enough:

```python
("leaf", label)
("split", j, t, left_subtree, right_subtree)
```

The build function returns one of these, and its recursive calls produce the subtrees. Prediction is a `while` loop that follows tuples until it reaches a leaf. No classes, no node IDs, and the structure mirrors the definition exactly.

## 6. Plan before you code

```
build(X, y, depth):
    leaf = ("leaf", majority label of y, ties to smallest)
    if depth == max_depth or len(y) < min_samples_split or y is pure: return leaf
    split = best split of (X, y) using this node's own midpoints
    if there is no split (all rows identical): return leaf
    mask = X[:, j] <= t
    return ("split", j, t, build(X[mask], y[mask], depth+1), build(X[~mask], y[~mask], depth+1))

predict(x): start at the root; while at a split, go left if x[j] <= t else right; return the leaf label
```

Compute the leaf label first: every early return uses it.

## 7. Build it one piece at a time

**Step 1: the split search, returning `None` when nothing can split.**

```python
def best_split(X, y):
    n, d = X.shape                                  # n samples at this node
    best, best_score = None, None
    for j in range(d):
        v = np.unique(X[:, j])                      # (r,) this node's sorted unique values
        for t in (v[:-1] + v[1:]) / 2.0:            # (r - 1,) node-local midpoints
            left = X[:, j] <= t                     # (n,) bool
            yl, yr = y[left], y[~left]
            score = len(yl) / n * gini(yl) + len(yr) / n * gini(yr)
            if best_score is None or score < best_score - 1e-12:
                best_score, best = score, (j, float(t))
    return best
```

This is problem 20's search, except it returns `None` instead of a `-1` sentinel and it doesn't need the score. Because it's called with the node's `X`, `np.unique` sees only the node's values, which gives node-local thresholds for free.

**Step 2: the stopping rules, before any search.**

```python
leaf = ("leaf", int(np.bincount(y).argmax()))       # majority; argmax picks the smallest tied label
if depth == max_depth or len(y) < min_samples_split or np.all(y == y[0]):
    return leaf
split = best_split(X, y)
if split is None:                                   # every row identical: no candidate threshold
    return leaf
```

`np.bincount(y)` counts each label; `argmax` returns the first maximum, so ties go to the smallest label, as the spec requires. `np.all(y == y[0])` is the purity test: `y == y[0]` broadcasts a scalar against the `(|S|,)` array.

**Step 3: recurse on the two halves.**

```python
j, t = split
m = X[:, j] <= t                                    # (|S|,) bool
return ("split", j, t,
        build(X[m], y[m], depth + 1, max_depth, min_samples_split),
        build(X[~m], y[~m], depth + 1, max_depth, min_samples_split))
```

`X[m]` has shape `(|L|, d)` and `X[~m]` has `(|R|, d)`. Both are non-empty because `t` is a midpoint between two values present in the node.

**Step 4: walk the tree for each test row.**

```python
def predict_one(node, x):                           # x: (d,)
    while node[0] == "split":
        _, j, t, left, right = node
        node = left if x[j] <= t else right
    return node[1]
```

The comparison is `<=`, the same as the training mask. Any mismatch sends points that sit exactly on a threshold to the side the tree never trained them for.

## 8. Full solution

```python
import numpy as np  # bincount for majorities and Gini, unique for node-local candidates


# Gini impurity of a non-empty label array: 1 - sum of squared class fractions
def gini(labels):
    p = np.bincount(labels) / len(labels)  # (max_label + 1,) class fractions
    return 1.0 - float(np.sum(p * p))  # 0 for a pure node, larger when mixed


# Best (feature, threshold) for this node's samples, or None if every row is identical
def best_split(X, y):
    n, d = X.shape  # n samples at this node, d features
    best, best_score = None, None  # None means no candidate seen yet
    for j in range(d):  # features in index order, for the tie rule
        v = np.unique(X[:, j])  # (r,) this node's sorted unique values, so thresholds are node-local
        for t in (v[:-1] + v[1:]) / 2.0:  # (r - 1,) midpoints, ascending
            left = X[:, j] <= t  # (n,) samples that go left, same comparison as prediction
            yl, yr = y[left], y[~left]  # labels on each side
            score = len(yl) / n * gini(yl) + len(yr) / n * gini(yr)  # size-weighted child impurity
            if best_score is None or score < best_score - 1e-12:  # strictly better: ties keep the earliest
                best_score, best = score, (j, float(t))  # remember the winner
    return best  # None only when no feature has a candidate


# Grow the subtree for samples (X, y) at this depth; returns a nested tuple
def build(X, y, depth, max_depth, min_samples_split):
    leaf = ("leaf", int(np.bincount(y).argmax()))  # majority label; argmax takes the smallest on ties
    # stopping rules 1-3: depth cap, too few samples to split, pure node
    if depth == max_depth or len(y) < min_samples_split or np.all(y == y[0]):
        return leaf  # this node predicts its majority label
    split = best_split(X, y)  # search only this node's samples
    if split is None:  # rule 4: all rows identical, nothing can separate them
        return leaf  # fall back to the majority label
    j, t = split  # the winning feature and threshold
    m = X[:, j] <= t  # (|S|,) mask of samples going left
    # split even if impurity doesn't drop (XOR needs that), and grow both children one level deeper
    return ("split", j, t,
            build(X[m], y[m], depth + 1, max_depth, min_samples_split),
            build(X[~m], y[~m], depth + 1, max_depth, min_samples_split))


# Route one test row x (d,) from the root to a leaf
def predict_one(node, x):
    while node[0] == "split":  # keep descending until a leaf
        _, j, t, left, right = node  # unpack the split node
        node = left if x[j] <= t else right  # <= exactly as in training, so ties at t go left
    return node[1]  # the leaf's label


# Fit a CART tree on the training data and predict every test row
def decision_tree_predict(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, max_depth: int, min_samples_split: int = 2) -> np.ndarray:
    tree = build(X_train, y_train, 0, max_depth, min_samples_split)  # the root is depth 0
    return np.array([predict_one(tree, x) for x in X_test], dtype=np.int64)  # (m,) predictions
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[0, 1, 0, 0]` | a split tie at the root, and the test point `2.5` exactly on the threshold goes left |
| Example 2 | `[0, 0, 0, 0]` | XOR at `max_depth = 1`: one split, both leaves tie 1-1 and predict the smaller label |
| Example 3 | `[0, 1, 1, 0]` | XOR at depth 2: the root split must happen even though it doesn't lower impurity |
| depth zero | all `1` | `max_depth = 0`: the root is a leaf; label counts are `[36, 44]` |
| xor-like 2d deep, xor-like 2d shallow | 60 labels each | XOR-shaped data at depths 6 and 2 |
| min samples split | 80 labels | `min_samples_split = 20` stops small nodes |
| min samples at boundary | `[0, 1, 0, 1, 1]` | a node of exactly 2 samples still splits with `min_samples_split = 2` |
| min samples equals node size | `[0, 0, 1, 1, 0]` | a node of 3 samples splits with `min_samples_split = 3` |
| test on thresholds | 40 labels | half-integer test values land exactly on midpoints |
| identical rows different labels | `[1, 0, 1]` | a node of three identical rows with labels `[2, 1, 1]` has no candidate; leaf predicts 1 |
| node-local thresholds | `[0, 0, 0, 1, 1, 1]` | the child's midpoint is 5.0, not the root's 2.0 |
| multiclass deep | 80 labels | three classes at depth 10, every rule at once |

## 10. Complexity

With `n` training rows, `d` features, depth limit `D` and `m` test rows:

- **Build:** each node of size $s$ costs $O(d\,s^2)$ with the direct scan. The nodes on one level partition the data, so a level costs at most $O(d\,n^2)$, and the whole tree $O(D\,d\,n^2)$. Sorted sweeps (problem 20) bring a level down to $O(d\,n \log n)$.
- **Predict:** $O(D)$ per test row, $O(mD)$ in total.
- **Memory:** $O(\text{nodes})$ for the tree, at most $2^{D+1} - 1$, plus the subset copies along the current recursion path, $O(nd)$ per level.

In production, a single deep tree overfits; the depth limit is the main knob. Random forests (many trees on bootstrap samples with random feature subsets) and gradient-boosted trees (many shallow trees fit to residuals) are what actually ship, and both call this build function hundreds of times. That's why libraries invest in histogram-based split search.

## 11. If you got Wrong Answer

- **Example 2 returns `[0, 1, 1, 0]` and "depth zero" isn't all `1`.** Your depth check is off by one (`depth > max_depth`, `wrong_depth_off_by_one.py`), so you grow one extra level. The root is depth 0.
- **Example 3 returns `[0, 0, 0, 0]`.** You only split when the score improves on the node's impurity. On XOR the root split has zero gain, so the tree stops at the root. The spec says to split anyway. With `<=` on `min_samples_split` (`wrong_min_samples_inclusive.py`), Example 3 also fails, since each depth-1 node has exactly 2 samples.
- **"min samples at boundary" returns `[0, 0, 0, 1, 1]`.** You stop when `len(y) <= min_samples_split`. A node with exactly that many samples may split (`wrong_min_samples_inclusive.py`). The same bug gives `[0, 0, 1, 1, 1]` on "min samples equals node size".
- **Example 1 returns `[0, 1, 0, 1]`.** You route with `x[j] < t` (`wrong_strict_routing.py`), so `2.5` goes right. It also fails "identical rows different labels", "test on thresholds" and three more.
- **"node-local thresholds" returns `[0, 1, 1, 1, 1, 1]`.** You computed candidate thresholds once from the full training set (`wrong_global_thresholds.py`), so the child split at `2.0` instead of `5.0`.
- **A crash on "identical rows different labels".** Your split search found no candidate and you tried to unpack `None`. Return a leaf.

## 12. Follow-ups an interviewer might ask

- *How do you stop a tree from overfitting?* Limit depth, raise `min_samples_split` or the minimum leaf size, require a minimum impurity decrease, or grow the full tree and prune it back with cost-complexity pruning (scikit-learn's `ccp_alpha`), choosing the strength by cross-validation (problem 31, stratified-k-fold).
- *How would you turn this into a random forest?* Train many trees, each on a bootstrap sample, considering a random subset of about $\sqrt d$ features at each split, and take the majority vote. Averaging decorrelated trees cuts variance.
- *How do you get class probabilities?* Store the leaf's label counts instead of just the majority, and return the normalized counts. They're poorly calibrated for deep trees (problem 33, expected-calibration-error).
- *What about missing values?* XGBoost and LightGBM learn a default direction at each split: they try sending all missing values left, then right, and keep the better score.
- *What's the per-feature importance?* Sum the weighted impurity decrease $\frac{|S|}{n}\Delta$ over every split on that feature. It's biased toward features with many unique values; permutation importance is the safer check.
