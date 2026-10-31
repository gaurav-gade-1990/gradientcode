Implement a **k-nearest-neighbors** classifier with majority voting.

For each row of `X_test`:

1. Compute the Euclidean distance to every row of `X_train`.
2. Order the training points by distance, ascending. If two points are equally far, the one with the **lower training index** comes first. Take the first `k`. These are the neighbors, ordered from nearest to farthest.
3. Count the labels among the `k` neighbors. The prediction is the label with the most votes.
4. **Vote ties.** If several labels share the top count, predict the one among them that appears **earliest in the neighbor order**, which is the tied label of the nearest neighbor.

Return an integer array of shape `(m,)` with one predicted label per test row.

**Constraints**

- `X_train` has shape `(n, d)` and `X_test` has shape `(m, d)`, with `1 <= n, m <= 300` and `1 <= d <= 10`
- `y_train` is an integer array of shape `(n,)` with labels in `[0, 20)`
- `1 <= k <= n`
