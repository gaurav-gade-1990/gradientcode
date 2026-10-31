Implement **Lloyd's algorithm** for k-means, starting from given centroids.

Let `C = init_centroids.copy()`, with shape `(k, d)`. Repeat at most `max_iter` times:

1. **Assign.** Give each point $x_i$ the label of its nearest centroid by squared Euclidean distance. On ties, use the **lowest** centroid index.
2. **Update.** Compute new centroids: centroid $j$ becomes the mean of the points labeled $j$. If no point is labeled $j$, centroid $j$ **keeps its current value**.
3. **Stop** early if the new centroids are exactly equal to `C`. Otherwise set `C` to the new centroids and continue.

Return a tuple `(centroids, labels)`:

- `centroids`: the final `C`, a float array of shape `(k, d)`.
- `labels`: an integer array of shape `(n,)` that assigns every point to its nearest centroid **in the returned `centroids`**, with the same tie rule. If the loop ran out of iterations, these labels come from one more assignment step. If `max_iter = 0`, the centroids are the initial ones.

**Constraints**

- `X` has shape `(n, d)` with `1 <= n <= 500`, `1 <= d <= 8`
- `1 <= k <= 10`
- `0 <= max_iter <= 100`
