Compute the **sample covariance matrix** of a data matrix `X` with shape `(n, d)`. Each row is an observation and each **column** is a feature (variable).

$$
\Sigma_{jk} = \frac{1}{n - 1} \sum_{i=1}^{n} (X_{ij} - \bar x_j)(X_{ik} - \bar x_k), \qquad \bar x_j = \frac{1}{n}\sum_{i=1}^{n} X_{ij}
$$

Return the `(d, d)` matrix $\Sigma$. Use the unbiased `n - 1` denominator (`ddof = 1`). Don't call `np.cov`.

**Constraints**

- `X` is a 2-D float array, `2 <= n <= 1000`, `1 <= d <= 50`
