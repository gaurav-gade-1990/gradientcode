## Approach

First build the distance matrix with broadcasting. The ordering is all that matters, so skip the square root:

$$
D_{ij} = \lVert x^{\text{test}}_i - x^{\text{train}}_j \rVert^2 .
$$

A **stable** argsort along each row orders the neighbors by distance and breaks ties by the lower training index, both in one call. Then vote:

```python
def knn_predict(X_train, y_train, X_test, k):
    diff = X_test[:, None, :] - X_train[None, :, :]
    D = np.sum(diff * diff, axis=-1)
    nn = np.argsort(D, axis=1, kind="stable")[:, :k]
    labels = y_train[nn]                       # (m, k), nearest first
    preds = np.empty(len(X_test), dtype=np.int64)
    for i, row in enumerate(labels):
        counts = np.bincount(row)
        top = counts.max()
        preds[i] = next(l for l in row if counts[l] == top)
    return preds
```

The vote-tie rule says "the tied class of the nearest neighbor". Scanning `row` from nearest to farthest and returning the first label with the top count implements exactly that.

## Common mistakes

- **`bincount(...).argmax()`.** It breaks ties by the smallest label, not by distance. The two rules disagree whenever $k$ is even or there are more than two classes.
- **An unstable sort.** The default `argsort` (quicksort) doesn't promise any order among equal distances. On grid data that can change which points make the cut.
- **Skipping the first neighbor.** `[:, 1:k+1]` is leave-one-out evaluation on the training set. Here the test points are separate, so the nearest neighbor counts.

## Complexity

- **Time:** $O(m n d)$ for distances plus $O(m n \log n)$ for sorting. `argpartition` would cut the sort to $O(mn)$, but it loses the stable tie order.
- **Space:** $O(m n d)$ for the broadcast difference. The $\lVert a\rVert^2 - 2ab + \lVert b\rVert^2$ trick cuts that to $O(mn)$, at the cost of floating-point noise on exact ties.
