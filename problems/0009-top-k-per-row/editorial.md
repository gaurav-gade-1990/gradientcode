## Approach: stable descending argsort

Sort each row's indices by value, largest first, and keep the first $k$. Two details make the answer unique.

1. **Descending.** `np.argsort` is ascending. Sort `-x` instead.
2. **Ties to the lower index.** A **stable** sort never reorders equal keys, so equal values stay in index order.

```python
def top_k(x, k):
    idx = np.argsort(-x, axis=1, kind="stable")[:, :k]
    vals = np.take_along_axis(x, idx, axis=1)
    return vals, idx
```

`np.take_along_axis` pairs each row of `idx` with the same row of `x`. It is shorthand for `x[np.arange(n)[:, None], idx]`.

### Faster for small $k$

A full sort is $O(m \log m)$ per row. `np.argpartition(-x, k - 1, axis=1)[:, :k]` finds a top-$k$ set in $O(m)$, but it returns it unordered, and when values tie at the cutoff it may keep a higher index over a lower one. To get the exact answer, sort the kept entries with a key that includes the index (`np.lexsort((idx, -vals))`) and handle cutoff ties separately. It pays off when $m$ is a vocabulary and $k$ is small.

## Common mistakes

- **Ascending sort reversed.** `argsort(x)[:, ::-1]` is descending, but reversing a stable sort also reverses ties, so the higher index wins.
- **`argpartition` alone.** The right set comes back in arbitrary order.
- **Sorting along `axis=0`.** That ranks each column, not each row.

## Complexity

- **Time:** $O(nm \log m)$ for the sort.
- **Space:** $O(nm)$ for the sorted indices.
