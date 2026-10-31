## Approach

Lloyd's algorithm alternates two steps, and each one can only lower the within-cluster sum of squares:

$$
\text{assign: } \ell_i = \arg\min_j \lVert x_i - c_j \rVert^2, \qquad
\text{update: } c_j = \frac{1}{|S_j|}\sum_{i \in S_j} x_i .
$$

The assignment step is a broadcast and an `argmin`. `argmin` returns the first minimum, which is exactly the lowest-index tie rule.

```python
def assign(X, C):
    diff = X[:, None, :] - C[None, :, :]
    return np.argmin(np.sum(diff * diff, axis=-1), axis=1)

def kmeans(X, init_centroids, max_iter):
    C = np.array(init_centroids, dtype=float)
    for _ in range(max_iter):
        labels = assign(X, C)
        new = C.copy()                       # empty clusters keep their value
        for j in range(len(C)):
            members = X[labels == j]
            if len(members):
                new[j] = members.mean(axis=0)
        if np.array_equal(new, C):
            break
        C = new
    return C, assign(X, C)
```

Converged centroids are a fixed point: reassigning against them gives the same labels. So the final `assign` call costs nothing in correctness, and it's what keeps `labels` consistent when `max_iter` cuts the loop short.

## Common mistakes

- **Empty clusters.** `X[labels == j].mean(axis=0)` of an empty selection is `nan` with a warning, and `nan` then poisons every distance to that centroid. Keep the old centroid, as the spec says.
- **Stale labels.** Returning the labels from before the last update leaves them out of sync with the centroids you return.
- **The wrong metric.** k-means minimizes squared Euclidean distance. L1 distance pairs with medians (k-medians), not means.

## Complexity

- **Time:** $O(T\, n k d)$ for $T$ iterations.
- **Space:** $O(n k d)$ for the broadcast. The expansion trick or a loop over centroids brings it down to $O(nk)$.
