## Approach

Gini impurity is the probability that two labels drawn at random (with replacement) from a node differ: $G = 1 - \sum_c p_c^2$. A split is good when it leaves children that are purer, weighted by their sizes.

Only the **order** of a feature's values matters, so the only distinct splits on feature $j$ fall between consecutive unique values. Midpoints are the conventional thresholds. They put the boundary halfway into the gap, which is also what scikit-learn does.

```python
def gini(labels):
    if len(labels) == 0:
        return 0.0
    p = np.bincount(labels) / len(labels)
    return 1.0 - np.sum(p * p)

def best_split(X, y):
    n, d = X.shape
    best, best_score = (-1, 0.0, gini(y)), None
    for j in range(d):
        v = np.unique(X[:, j])                      # sorted
        for t in (v[:-1] + v[1:]) / 2.0:
            left = X[:, j] <= t
            score = left.sum() / n * gini(y[left]) + (~left).sum() / n * gini(y[~left])
            if best_score is None or score < best_score - 1e-12:
                best_score, best = score, (j, float(t), float(score))
    return best
```

### A faster scan

Sort each column once, then sweep left to right while keeping per-class counts for the left side. Each candidate then costs $O(C)$ instead of $O(n)$. That's what real tree libraries do, and it brings the search down to $O(d\, n \log n)$.

## Common mistakes

- **Thresholds at the values.** `x <= v_k` makes the same partition as `x <= (v_k + v_{k+1})/2`, but the threshold it returns is different. Unseen test points that fall in the gap then go the other way.
- **Unweighted children.** Averaging $G(L)$ and $G(R)$ equally rewards splitting off one pure sample.
- **`<=` in the comparison.** Then the *last* tied candidate wins, which breaks the tie rule.

## Complexity

- **Time:** $O(d\, n^2)$ for this direct version, or $O(d\, n \log n)$ with sorted sweeps.
- **Space:** $O(n)$.
