Implement **k-means++** seeding (Arthur & Vassilvitskii, 2007). Draw the randomness from the given uniforms `u`, so the result is deterministic.

`u` has length `k`, and every entry is in $[0, 1)$. Choose `k` row indices of `X` like this:

1. **First center.** $c_0 = \lfloor u_0 \cdot n \rfloor$.
2. **Each later center** $j = 1, \dots, k-1$:
   - Let $D^2_i$ be the squared Euclidean distance from $x_i$ to its **nearest already-chosen center**.
   - Let $S_i = \sum_{l \le i} D^2_l$ (the cumulative sum), and let $\tau = u_j \cdot S_{n-1}$.
   - Pick $c_j$ = the **smallest** index $i$ with $S_i > \tau$ (strictly greater). This is `np.searchsorted(S, tau, side="right")`.

So each point is chosen with probability proportional to $D^2_i$, and a point with $D^2_i = 0$, such as one already chosen, can never be chosen.

Return an integer array of shape `(k,)` with the chosen indices, in the order they were chosen. The initial centroids are `X[indices]`.

**Constraints**

- `X` has shape `(n, d)` with `1 <= n <= 500`, `1 <= d <= 8`
- `1 <= k <= n`, and `X` has at least `k` distinct rows
- `0 <= u[j] < 1`
