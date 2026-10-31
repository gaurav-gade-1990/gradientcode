Find the best **binary split** of a dataset for a classification tree, scored by weighted **Gini impurity**.

The Gini impurity of a set $S$ of labels is

$$
G(S) = 1 - \sum_{c} p_c^2, \qquad p_c = \frac{|\{ i \in S : y_i = c \}|}{|S|}.
$$

A split $(j, t)$ sends sample $i$ **left** if $X_{ij} \le t$ and **right** otherwise. Its score is

$$
\text{score}(j, t) = \frac{|L|}{n} G(L) + \frac{|R|}{n} G(R).
$$

**Candidates.** For each feature $j$, take the sorted unique values $v_1 < v_2 < \dots < v_r$ of column $j$. The candidate thresholds are the midpoints $t = (v_k + v_{k+1}) / 2$ for $k = 1, \dots, r-1$. A constant feature has no candidates.

**Search order and ties.** Visit the features in order $j = 0, 1, \dots$, and the thresholds of each feature in ascending order. A candidate becomes the new best only if its score is **lower than the current best by more than `1e-12`**. So among (numerically) tied candidates, the one with the smallest feature index wins, and then the one with the smallest threshold.

Return a tuple `(feature, threshold, score)` with types `(int, float, float)`. If no feature has a candidate (every column is constant), return `(-1, 0.0, G(y))`.

**Constraints**

- `X` has shape `(n, d)` with `1 <= n <= 300` and `1 <= d <= 8`
- `y` holds non-negative integers below `10`
