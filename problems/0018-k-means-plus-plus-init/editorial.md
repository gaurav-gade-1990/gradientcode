## Approach

k-means++ spreads the seeds out. Each new center is drawn with probability proportional to $D^2(x)$, the squared distance to the nearest center chosen so far. In expectation, this seeding is already $O(\log k)$-competitive with the optimal clustering.

Sampling from a discrete distribution with one uniform $u$ is **inverse-CDF** sampling. Build the cumulative weights and find where $u \cdot \text{total}$ falls:

$$
S_i = \sum_{l \le i} D^2_l, \qquad c = \min\{ i : S_i > u\, S_{n-1} \}.
$$

```python
def kmeans_pp_init(X, k, u):
    n = X.shape[0]
    idx = [int(u[0] * n)]
    D2 = np.sum((X - X[idx[0]]) ** 2, axis=1)
    for j in range(1, k):
        cum = np.cumsum(D2)
        c = int(np.searchsorted(cum, u[j] * cum[-1], side="right"))
        idx.append(c)
        D2 = np.minimum(D2, np.sum((X - X[c]) ** 2, axis=1))
    return np.array(idx)
```

Keeping `D2` as a running minimum makes each step cost $O(nd)$, instead of recomputing the distance to every chosen center.

### Why `side="right"`?

A point with $D^2_i = 0$ leaves the cumulative sum flat: $S_i = S_{i-1}$. With `side="left"`, a target equal to $S_i$ returns $i$, so a zero-weight point (an existing center) can be picked again, for example when $u = 0$. `side="right"` always skips flat steps.

## Common mistakes

- **Distances instead of squared distances.** The method is called $D^2$ sampling for a reason. Plain distances weight far points less.
- **Only the newest center.** $D^2$ is the distance to the *nearest* chosen center, which is a running minimum over all of them.
- **`side="left"`.** It can re-select a center at an exact boundary.

## Complexity

- **Time:** $O(k\, n d)$.
- **Space:** $O(n)$ for `D2` and the cumulative sum.
