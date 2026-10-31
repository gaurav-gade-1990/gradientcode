## Approach

Cosine similarity is a dot product between unit vectors. Normalize both sides once, and a single matrix multiply gives every query-document score.

$$
S = \hat Q \hat D^\top, \qquad \hat x = \frac{x}{\lVert x\rVert}
$$

Then sort each row by descending score. A **stable** sort of `-S` keeps equal scores in index order, which is exactly the tie-break you need.

```python
def _unit_rows(x):
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(n == 0, 1.0, n)

S = _unit_rows(queries) @ _unit_rows(docs).T
idx = np.argsort(-S, axis=1, kind="stable")[:, :k]
scores = np.take_along_axis(S, idx, axis=1)
```

A zero row divided by `1` stays zero, so its similarity with everything is `0`.

For very large `n_docs` you could use `np.argpartition` to find the top `k` in $O(n)$, then sort only those `k`. Be careful: `argpartition` doesn't respect the tie-break on its own.

## Common mistakes

- **Raw dot product.** Without normalizing, long document vectors win regardless of direction.
- **Reversing an ascending sort.** `argsort(S)[:, ::-1]` puts the higher index first on ties.
- **No zero-norm guard.** `0 / 0` gives `nan`, and `nan` sorts unpredictably.

## Complexity

- **Time:** $O(QNd)$ for the similarity matrix plus $O(QN\log N)$ for the sort.
- **Space:** $O(QN)$ for the similarity matrix. Production systems use approximate indexes (HNSW, IVF) so they don't have to touch every document.
