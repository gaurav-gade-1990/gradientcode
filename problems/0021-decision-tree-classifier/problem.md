Grow a **CART classification tree** with Gini impurity on `(X_train, y_train)`, then return its predictions for `X_test`.

**Splitting a node.** Score splits only on the samples that reach the node, using the same rules as *Best Split by Gini Impurity*:

- candidates $(j, t)$, where $t$ is a midpoint between consecutive sorted unique values of feature $j$ **among the node's samples**,
- left if $x_j \le t$, right otherwise,
- score $= \frac{|L|}{|S|} G(L) + \frac{|R|}{|S|} G(R)$, where $|S|$ is the node's sample count,
- visit features in index order and thresholds ascending. A candidate replaces the best only if its score is lower by more than `1e-12`.

**Growing.** The root has depth 0. A node with sample set $S$ at depth $\delta$ becomes a **leaf** if any of these holds:

1. $\delta = $ `max_depth`,
2. $|S| <$ `min_samples_split`,
3. every label in $S$ is the same (the node is pure),
4. no feature has a candidate threshold (all of the node's rows are identical).

Otherwise, split the node with its best split, even if the score is no lower than the node's own impurity, and grow both children at depth $\delta + 1$.

**Leaves** predict the most common label among their training samples. On ties, they predict the **smallest** label.

**Predicting.** Each test row starts at the root and goes left when $x_j \le t$, right otherwise, until it reaches a leaf.

Return an integer array of shape `(m,)`.

**Constraints**

- `X_train` has shape `(n, d)` with `1 <= n <= 200` and `1 <= d <= 6`, and `X_test` has shape `(m, d)` with `1 <= m <= 200`
- `y_train` holds non-negative integers below `10`
- `0 <= max_depth <= 10`, `2 <= min_samples_split <= n + 1`
