## Approach: fit once, apply twice

Compute per-column statistics from the training set, guard the zero-variance columns, then broadcast the same `(d,)` vectors over both sets:

$$
Z = \frac{X - \mu}{\sigma}, \qquad \sigma_j \leftarrow 1 \text{ if } \sigma_j = 0
$$

```python
def standardize(X_train, X_test):
    mu = X_train.mean(axis=0)
    sigma = X_train.std(axis=0)
    sigma = np.where(sigma == 0, 1.0, sigma)
    return (X_train - mu) / sigma, (X_test - mu) / sigma
```

`X_train.std(axis=0)` defaults to `ddof=0`, the population std, which is what `StandardScaler` uses.

### Why fit on train only?

At prediction time you see one example at a time, so test statistics don't exist. Fitting the scaler on the test set, or on train plus test, leaks information about the evaluation data into preprocessing and inflates your scores.

## Common mistakes

- **Fitting on the test set.** The training output looks right, and the test output is centered on its own mean.
- **`ddof=1`.** `np.std` and `StandardScaler` both default to the population std. `pandas.Series.std` defaults to `ddof=1`, which is a common source of mismatch.
- **Adding a tiny `eps` instead of a guard.** On a constant column, `(x - mu) / 1e-12` explodes for any test value that differs from the training constant.

## Complexity

- **Time:** $O((n + m)d)$.
- **Space:** $O((n + m)d)$ for the outputs.
