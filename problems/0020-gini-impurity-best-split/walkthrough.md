## 1. What the problem is really asking

This is the inner loop of every decision tree: given the samples that reached one node, find the single question "is feature `j` at most `t`?" that best separates the classes. A tree is just this search applied recursively (problem 21, decision-tree-classifier).

Under the story, it's an **exhaustive search with a deterministic tie rule**. For each feature, every distinct way to cut the sorted values into "low" and "high" is a candidate. You score each one with weighted Gini impurity and keep the lowest. There are at most $d(n-1)$ candidates, and at these sizes you can afford to score each one directly.

The judge compares the whole tuple `(feature, threshold, score)`: the feature index, the threshold to `rtol = 1e-9`, and the score. So it isn't enough to find *a* best partition. You have to return the midpoint threshold, and among tied candidates, the one the spec's search order finds first.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `X` | `(n, d)` float | the samples at this node | one column at a time; candidates come from its unique values |
| `y` | `(n,)` int, `0..9` | class labels | `np.bincount` for class fractions |
| return | `(int, float, float)` | best feature, threshold, score | `(-1, 0.0, G(y))` if no feature can split |

Three details are easy to miss:

- **Thresholds are midpoints**, not data values. `x <= 2` and `x <= 2.5` make the same partition of `[1, 2, 3, 4]`, but they return different thresholds, and only the midpoint is accepted.
- **Duplicates collapse.** Candidates come from the *unique* values. In Example 2, feature 1 is `[10, 20, 10, 30]`, which has unique values `[10, 20, 30]` and only two midpoints, `15` and `25`.
- **A non-improving split still counts.** The first candidate always becomes the best, even when its score equals $G(y)$. In "tie across features" the best score is `0.5`, the same as the parent's impurity, and the answer is still `(0, 0.5, 0.5)`, not `-1`.

## 3. The math

**Gini impurity.** For a set $S$ with class fractions $p_c$,

$$
G(S) = 1 - \sum_c p_c^2 .
$$

It has a clean meaning. Draw two labels from $S$ independently, with replacement. The probability they are both class $c$ is $p_c^2$, so the probability they **differ** is

$$
P(\text{differ}) = 1 - \sum_c p_c^2 = \sum_c p_c (1 - p_c) = G(S).
$$

A pure node has one $p_c = 1$, so $G = 0$. With $C$ classes in equal shares, $G = 1 - C \cdot \frac{1}{C^2} = 1 - \frac1C$: `0.5` for two balanced classes.

**The split score.** A split sends $|L|$ samples left and $|R| = n - |L|$ right:

$$
\text{score}(j, t) = \frac{|L|}{n} G(L) + \frac{|R|}{n} G(R).
$$

This is the expected impurity of the child that a random sample lands in. The weights matter. Without them, splitting off one sample gives a pure child with $G = 0$, which pulls the average down even though the big child is as mixed as before.

**Why midpoints between unique values are enough.** The partition $\{i : X_{ij} \le t\}$ only changes when $t$ crosses a data value. For any $t$ in the gap $[v_k, v_{k+1})$, the left set is exactly the samples with value $\le v_k$. So each gap gives one distinct partition, there are $r - 1$ gaps for $r$ unique values, and any $t$ inside a gap scores the same. The midpoint $\frac{v_k + v_{k+1}}{2}$ is the conventional representative: it's the threshold that is farthest from both training values, so an unseen point in the gap goes to whichever side it is closer to.

**Floating-point ties.** Two partitions with mirror-image label counts, like `[0] | [1, 0, 1, 0, 1]` and `[0, 1, 0, 1, 0] | [1]`, have the same exact score, but floating-point arithmetic can compute them in different orders and land a few ulps apart. Comparing `score < best - 1e-12` treats any difference that small as a tie, so the earlier candidate keeps its place.

## 4. Trace an example by hand

**Example 2.** `X` is `(4, 2)`, `y = [0, 1, 0, 1]`, and $G(y) = 0.5$.

| feature | $t$ | left labels | right labels | $G(L)$ | $G(R)$ | score | new best? |
|---|---|---|---|---|---|---|---|
| 0 | 1.5 | `[0]` | `[1, 0, 1]` | 0 | 0.4444 | 0.3333 | yes (first) |
| 0 | 2.5 | `[0, 1]` | `[0, 1]` | 0.5 | 0.5 | 0.5 | no |
| 0 | 3.5 | `[0, 1, 0]` | `[1]` | 0.4444 | 0 | 0.3333 | no (a tie, not lower) |
| 1 | 15.0 | `[0, 0]` | `[1, 1]` | 0 | 0 | **0** | **yes** |
| 1 | 25.0 | `[0, 1, 0]` | `[1]` | 0.4444 | 0 | 0.3333 | no |

The answer is `(1, 15.0, 0.0)`. Note the threshold `15.0`: the rows with value 10 (rows 0 and 2) both go left, and both have label 0.

**The hidden "tie within feature" case** shows the tie rule. `X` is `0..5` in one column, `y = [0, 1, 0, 1, 0, 1]`:

| $t$ | score |
|---|---|
| 0.5 | **0.4** |
| 1.5 | 0.5 |
| 2.5 | 0.4444 |
| 3.5 | 0.5 |
| 4.5 | 0.4 |

`0.5` and `4.5` tie at `0.4`. Scanning thresholds ascending and replacing only on a strictly lower score keeps `0.5`. The expected answer is `(0, 0.5, 0.4)`. With a `<=` comparison you'd return `4.5`.

## 5. Plan before you code

```
best = (-1, 0.0, G(y)); best_score = None
for j in 0 .. d-1:
    v = sorted unique values of column j          # (r,)
    for t in midpoints of v, ascending:           # (r - 1,)
        left = column j <= t                       # (n,) boolean
        score = |L|/n * G(y[left]) + |R|/n * G(y[~left])
        if best_score is None or score < best_score - 1e-12:
            best_score = score; best = (j, t, score)
return best
```

| situation | result |
|---|---|
| every column constant | the loop never runs: `(-1, 0.0, G(y))` |
| first candidate seen | always becomes the best |
| a later candidate ties within `1e-12` | ignored, so the earliest wins |

## 6. Build it one piece at a time

**Step 1: Gini of a label array.**

```python
def gini(labels):
    if len(labels) == 0:
        return 0.0
    p = np.bincount(labels) / len(labels)        # (max_label + 1,) class fractions
    return 1.0 - float(np.sum(p * p))
```

`np.bincount` counts how often each integer appears; dividing by the length turns counts into fractions. Labels that never appear contribute 0 to the sum, so the extra slots don't matter. The empty guard is defensive: with midpoint thresholds both sides always have at least one sample, because $v_k \le t$ for the left and $v_{k+1} > t$ for the right.

**Step 2: candidates for one feature.**

```python
v = np.unique(X[:, j])                            # (r,) sorted unique values
for t in (v[:-1] + v[1:]) / 2.0:                  # (r - 1,) midpoints, ascending
```

`v[:-1]` is every value but the last, and `v[1:]` is every value but the first, so adding them pairs each value with its successor. For a constant column, `r = 1` and the midpoint array is empty, so the loop body never runs.

**Step 3: score a candidate.**

```python
left = X[:, j] <= t                               # (n,) boolean mask
yl, yr = y[left], y[~left]                        # labels on each side
score = len(yl) / n * gini(yl) + len(yr) / n * gini(yr)
```

`~left` flips the mask, so `y[~left]` is the right side. The `<=` matches the spec's "left if $X_{ij} \le t$". Because `t` is a midpoint, no value equals it, so `<` would give the same partition here; with value thresholds it wouldn't.

**Step 4: keep the best, earliest on ties.**

```python
if best_score is None or score < best_score - 1e-12:
    best_score = score
    best = (j, float(t), float(score))
```

`best_score is None` makes the first candidate win unconditionally. `float(t)` turns a NumPy scalar into a plain Python float for the tuple.

## 7. Full solution

```python
import numpy as np  # bincount for class fractions, unique for sorted candidate values


# Gini impurity of a label array: the chance that two random draws (with replacement) disagree
def gini(labels):
    if len(labels) == 0:  # defensive: midpoint splits never leave a side empty
        return 0.0  # treat an empty side as pure so it adds nothing
    p = np.bincount(labels) / len(labels)  # (max_label + 1,) class fractions
    return 1.0 - float(np.sum(p * p))  # 1 - sum p_c^2, as a plain float


# Exhaustive search over (feature, midpoint) splits; returns (feature, threshold, weighted Gini)
def best_split(X: np.ndarray, y: np.ndarray) -> tuple:
    n, d = X.shape  # n samples at this node, d features
    best = (-1, 0.0, gini(y))  # the answer when no feature can split (every column constant)
    best_score = None  # no candidate seen yet, so the first one always wins
    for j in range(d):  # features in index order, for the tie rule
        v = np.unique(X[:, j])  # (r,) sorted unique values; duplicates give no extra splits
        for t in (v[:-1] + v[1:]) / 2.0:  # (r - 1,) midpoints, ascending; empty for a constant column
            left = X[:, j] <= t  # (n,) mask of samples that go left
            yl, yr = y[left], y[~left]  # labels on each side of the split
            score = len(yl) / n * gini(yl) + len(yr) / n * gini(yr)  # size-weighted child impurity
            if best_score is None or score < best_score - 1e-12:  # strictly better, so ties keep the earliest
                best_score = score  # remember the score to beat
                best = (j, float(t), float(score))  # plain Python types for the returned tuple
    return best  # (feature, threshold, score)
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `(0, 2.5, 0)` | a perfect split at the middle midpoint |
| Example 2 | `(1, 15, 0)` | duplicate values collapse; a later feature wins with a lower score |
| noisy single informative feature | `(2, 0.368302, 0.223199)` | finds the informative feature among noise |
| integer features with ties | `(0, 0.5, 0.608333)` | many duplicate values; three classes |
| all constant | `(-1, 0, 0.48)` | no candidates; return $G(y)$ for `[0, 1, 1, 0, 1]` |
| pure node | `(0, -1.99888, 0)` | every split scores 0; the first threshold of feature 0 wins |
| tie across features | `(0, 0.5, 0.5)` | equal scores on two features; the lower index wins |
| tie within feature | `(0, 0.5, 0.4)` | equal scores at `0.5` and `4.5`; the lower threshold wins |
| two samples | `(0, 2, 0)` | the smallest splittable node; feature 1 is constant |
| larger multiclass | `(1, -0.105, 0.392867)` | 250 rows, 6 features, three classes |

## 9. Complexity

With `n` samples, `d` features and `C` classes:

- **Time:** $O(d\,n^2)$ for this direct version: up to $n - 1$ candidates per feature, each building an `(n,)` mask and two `bincount`s.
- **Memory:** $O(n)$ for the mask and the label slices.

Real tree libraries (scikit-learn, XGBoost, LightGBM) do better. Sort each column once, $O(n \log n)$, then sweep left to right, moving one sample at a time from the right counts to the left counts. Each candidate costs $O(C)$ to score, so a feature costs $O(n \log n + nC)$. Gradient-boosting libraries go further and bucket each feature into about 256 histogram bins, so the sweep is over bins instead of samples. That's what makes training on millions of rows practical.

## 10. If you got Wrong Answer

- **The threshold is a data value, like `2` instead of `2.5`.** You used `v[:-1]` as thresholds instead of midpoints (`wrong_threshold_at_value.py`). The partition is the same, so the score matches, but the threshold doesn't. This fails every case except "all constant". On Example 2 it returns `(1, 10, 0)`.
- **"tie within feature" returns `(0, 4.5, 0.4)`, and "pure node" and "tie across features" fail too.** Your comparison lets ties replace the best (`score <= best + 1e-12`, `wrong_last_tie_wins.py`), so the *last* tied candidate wins.
- **"tie within feature" returns score `0.24`.** You averaged the two children equally instead of by size (`wrong_unweighted.py`). For `t = 0.5`, that's $\frac{0 + 0.48}{2} = 0.24$ instead of $\frac16 \cdot 0 + \frac56 \cdot 0.48 = 0.4$. The noisy and larger cases fail the same way, because the unweighted score rewards chipping off a single sample.
- **"all constant" crashes or returns a split.** Make sure the default `best` is `(-1, 0.0, gini(y))` and that a constant column yields no midpoints.
- **The score is off by tiny amounts on ties.** Use the `1e-12` tolerance exactly as the spec says, rather than `==` or a looser `1e-6`.

## 11. Follow-ups an interviewer might ask

- *Why Gini rather than entropy?* Entropy, $-\sum_c p_c \log p_c$, is the other standard choice (it gives information gain). The two pick the same split most of the time. Gini avoids the logarithm, so it's slightly cheaper, which is why it's scikit-learn's default.
- *How do you make this $O(n \log n)$ per feature?* Sort once, sweep with running class counts, and update the score in $O(C)$ per step (section 9).
- *How would you handle a categorical feature?* For two classes, sort the categories by their fraction of class 1 and treat that order as numeric; the best subset split is then a threshold on that order. For more classes it's harder, so libraries often one-hot encode (problem 5, one-hot-encoding) or use target encoding.
- *What about regression trees?* Replace Gini with the variance of the targets on each side; the weighted score becomes the sum of squared errors. The sweep is the same, with running sums of $y$ and $y^2$.
- *How does a tree use this?* Call it at the root, split the data, and recurse on each side until a depth limit or a pure node (problem 21, decision-tree-classifier).
