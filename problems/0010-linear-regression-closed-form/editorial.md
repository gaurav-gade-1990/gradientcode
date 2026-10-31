## Approach

Fold the bias into the weights. With $A = [X \;\; \mathbf{1}]$ and $\theta = [w; b]$, the model is $A\theta \approx y$. Setting the gradient of $\lVert A\theta - y \rVert^2$ to zero gives the **normal equations**:

$$
A^\top A\, \theta = A^\top y .
$$

When $A$ has full column rank, $A^\top A$ is invertible and the solution is unique. When it doesn't (a duplicated or constant column, or fewer rows than unknowns), every solution of the normal equations is a minimizer. The pseudo-inverse picks the one with the smallest norm: $\theta = A^{+} y$.

`np.linalg.lstsq` computes exactly that through an SVD, and it never forms $A^\top A$:

```python
def fit_linear_regression(X, y):
    A = np.hstack([X, np.ones((X.shape[0], 1))])
    theta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return theta[:-1], float(theta[-1])
```

## Common mistakes

- **No bias column.** The fit is forced through the origin. Any data with a nonzero mean is fit badly.
- **`inv(A.T @ A)`.** It fails, or returns garbage, when the columns are dependent. Even when it works, forming $A^\top A$ squares the condition number. Prefer `lstsq` or `solve`.
- **A constant feature.** A column of 3s is collinear with the bias column, so the problem is rank-deficient. The minimum-norm rule splits the intercept between them.

## Complexity

- **Time:** $O(n d^2)$ for the SVD-based solve (with $d$ counting the bias column).
- **Space:** $O(n d)$ for the augmented matrix.
