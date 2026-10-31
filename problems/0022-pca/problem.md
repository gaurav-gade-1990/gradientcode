Implement **PCA** through an eigendecomposition of the sample covariance matrix.

Given data `X` of shape `(n, d)`, with rows as samples, and a target dimension `k`:

1. Center the data: $X_c = X - \bar x$, where $\bar x$ is the column mean.
2. Form the sample covariance $\Sigma = \frac{1}{n-1} X_c^\top X_c$.
3. Take its eigenvalues $\lambda_1 \ge \lambda_2 \ge \dots \ge \lambda_d$ (sorted **descending**) and the unit eigenvectors $v_1, \dots, v_d$.
4. **Fix the sign** of each eigenvector: flip $v_i$ if its entry with the largest absolute value is negative. If several entries tie for the largest absolute value, use the first one.

Return a tuple `(Z, components, explained_variance_ratio)`:

- `components`: shape `(k, d)`, where row `i` is $v_{i+1}$ (the components are **rows**),
- `Z = X_c @ components.T`: the projected data, shape `(n, k)`,
- `explained_variance_ratio`: shape `(k,)`, the values $\lambda_i / \sum_{l=1}^{d} \lambda_l$.

**Constraints**

- `2 <= n <= 300`, `1 <= d <= 10`, `1 <= k <= d`
- In every test, the top `k + 1` eigenvalues (or all of them, when `k = d`) are distinct, so each component is unique up to sign
- `X` is not constant, so the total variance is positive
