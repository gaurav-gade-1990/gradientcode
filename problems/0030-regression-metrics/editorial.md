## Approach

Compute the residuals once and read every metric off them:

```python
def regression_metrics(y_true, y_pred):
    e = y_true - y_pred
    mse = np.mean(e ** 2)
    ss_res = np.sum(e ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    if ss_tot == 0:
        r2 = 1.0 if ss_res == 0 else 0.0
    else:
        r2 = 1.0 - ss_res / ss_tot
    return {"mse": mse, "rmse": np.sqrt(mse), "mae": np.mean(np.abs(e)), "r2": r2}
```

### What $R^2$ measures

$SS_{\text{tot}}$ is the error of the best constant model, which always predicts $\bar y$. $R^2$ is the fraction of that error your model removes. $R^2 = 0$ means you are no better than the mean, and a negative $R^2$ means you are worse. It is not the square of anything here, so negative values are fine.

### MSE vs MAE

MSE squares the residuals, so one big miss dominates. MAE weights all misses linearly, so it is more robust to outliers. RMSE is in the same units as $y$, which makes it easier to read than MSE.

## Common mistakes

- **Centering $SS_{\text{tot}}$ on the predictions.** The baseline is the mean of the **targets**.
- **Dividing by zero for a constant target.** `0 / 0` is `nan` and `x / 0` is `-inf`. Handle the case explicitly.
- **RMSE as the mean of absolute errors.** $\sqrt{\text{mean}(e^2)}$ is not $\text{mean}(\sqrt{e^2})$. The latter is MAE.

## Complexity

- **Time:** $O(n)$.
- **Space:** $O(n)$ for the residuals.
