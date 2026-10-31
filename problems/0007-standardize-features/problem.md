Implement **z-score standardization** the way a scikit-learn `StandardScaler` does it: fit on the training set, then transform both sets with the training statistics.

For each feature (column) `j`, compute from `X_train` only:

$$
\mu_j = \frac{1}{n}\sum_i X^{\text{train}}_{ij}, \qquad \sigma_j = \sqrt{\frac{1}{n}\sum_i \big(X^{\text{train}}_{ij} - \mu_j\big)^2}
$$

That is the **population** standard deviation (`ddof = 0`). If $\sigma_j = 0$ (a constant column), use $\sigma_j = 1$ instead, so the column is only centered.

Then transform each set with the same $\mu$ and $\sigma$:

$$
Z_{ij} = \frac{X_{ij} - \mu_j}{\sigma_j}
$$

Return a tuple `(Z_train, Z_test)` with the same shapes as `X_train` and `X_test`. Don't modify the inputs in place.

**Constraints**

- `X_train` has shape `(n, d)` with `1 <= n <= 1000`, `1 <= d <= 50`
- `X_test` has shape `(m, d)` with `0 <= m <= 1000`
- entries are finite floats
