## Approach: recursive greedy splitting

CART grows a tree top-down. At each node it picks the single split that most reduces the weighted Gini impurity of the node's own samples, then recurses on the two halves. Nothing is ever revisited. The algorithm is greedy, and the deterministic tie rule makes the tree unique.

Keep the stopping rules ahead of the split search. They're cheap to check, and they define the tree:

```python
def build(X, y, depth):
    leaf = ("leaf", int(np.bincount(y).argmax()))   # ties -> smallest label
    if depth == max_depth or len(y) < min_samples_split or np.all(y == y[0]):
        return leaf
    split = best_split(X, y)                        # node-local midpoints
    if split is None:                               # all rows identical
        return leaf
    j, t = split
    m = X[:, j] <= t
    return ("split", j, t, build(X[m], y[m], depth + 1), build(X[~m], y[~m], depth + 1))

def predict_one(node, x):
    while node[0] == "split":
        _, j, t, left, right = node
        node = left if x[j] <= t else right
    return node[1]
```

`best_split` is the scan from *Best Split by Gini Impurity*, run on the node's subset. A child's midpoints come from **its own** unique values. The partition might match one made from a root-level midpoint, but the threshold is different, and that changes where unseen test points go.

### Why split when the score doesn't improve?

On XOR, every first split leaves the impurity at 0.5. A rule that requires improvement stops at the root. Splitting anyway lets the second level separate the classes perfectly. That's scikit-learn's default (`min_impurity_decrease=0`).

## Common mistakes

- **Depth off by one.** The root is depth 0, so `max_depth = 1` means one split. Testing `depth > max_depth` grows an extra level.
- **`<=` vs `<` for `min_samples_split`.** A node with exactly `min_samples_split` samples **may** split.
- **Routing with `<`.** It must use the same comparison as training. Test points that land exactly on a threshold go to the wrong side.
- **Global thresholds.** Candidates computed once from the full training set give different thresholds deeper in the tree.

## Complexity

- **Time:** $O(D\, d\, n^2)$ to build with the direct split scan, where $D$ is the depth (each level touches each sample once per candidate). Sorted sweeps bring it down to $O(D\, d\, n \log n)$. Prediction is $O(D)$ per test row.
- **Space:** $O(\text{nodes})$ for the tree, plus $O(n)$ for the index subsets along the recursion.
