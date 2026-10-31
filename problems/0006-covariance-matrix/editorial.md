## Approach: center, then one matmul

Center each column, then every pairwise covariance is a dot product of two centered columns. All $d^2$ of them at once:

$$
X_c = X - \mathbf{1}\bar x^\top, \qquad \Sigma = \frac{X_c^\top X_c}{n - 1}
$$

```python
def covariance(X):
    n = X.shape[0]
    Xc = X - X.mean(axis=0, keepdims=True)
    return Xc.T @ Xc / (n - 1)
```

### Why $n - 1$?

Centering uses the sample mean, which is fit to the same data, so the centered deviations are slightly too small on average. Dividing by $n - 1$ (Bessel's correction) makes the estimate unbiased. `np.cov` defaults to `ddof=1`, while `np.var` defaults to `ddof=0`. That mismatch catches people.

## Common mistakes

- **`ddof=0`.** Dividing by `n` gives the maximum-likelihood estimate, not the sample covariance.
- **Skipping the centering.** `X.T @ X / (n - 1)` is a second-moment matrix. It only equals the covariance when every column has mean zero.
- **Rows as variables.** `np.cov(X)` treats rows as variables by default, which returns an `(n, n)` matrix. Use `rowvar=False`, or transpose.

## Complexity

- **Time:** $O(nd^2)$ for the product.
- **Space:** $O(nd)$ for the centered copy, plus $O(d^2)$ for the output.
