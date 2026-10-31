## Approach

PCA finds the orthogonal directions of maximum variance. The variance of the data projected onto a unit vector $v$ is $v^\top \Sigma v$, and it's maximized by the top eigenvector of $\Sigma$. The next direction, orthogonal to the first, is the second eigenvector, and so on.

```python
def pca(X, k):
    Xc = X - X.mean(axis=0)
    cov = Xc.T @ Xc / (X.shape[0] - 1)
    vals, vecs = np.linalg.eigh(cov)                 # ascending, columns
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    comps = vecs[:, :k].T.copy()                     # rows
    pivot = np.argmax(np.abs(comps), axis=1)
    comps *= np.sign(comps[np.arange(k), pivot])[:, None]
    return Xc @ comps.T, comps, vals[:k] / vals.sum()
```

Use `eigh`, not `eig`. The covariance is symmetric, and `eigh` guarantees real eigenvalues and orthonormal eigenvectors.

### The sign convention

If $v$ is an eigenvector, so is $-v$. Different libraries, and even different LAPACK builds, return different signs. Making the largest-magnitude entry positive gives every correct implementation the same answer. scikit-learn applies a similar `svd_flip` convention.

### The SVD alternative

$X_c = U S V^\top$ gives the components as the rows of $V^\top$, with eigenvalues $S^2/(n-1)$. It never forms $X_c^\top X_c$, so it's more accurate when the data is ill-conditioned.

## Common mistakes

- **No centering.** The top "component" then points at the data mean instead of along the spread.
- **Ascending order.** `eigh` sorts the eigenvalues smallest first. Forgetting to reverse returns the *least* important directions.
- **Ignoring the sign.** Your answer can be correct and still disagree with every other implementation.

## Complexity

- **Time:** $O(n d^2)$ to form the covariance, plus $O(d^3)$ for the eigendecomposition.
- **Space:** $O(n d + d^2)$.
