Compute four standard regression metrics. Let $e_i = y_i - \hat y_i$ be the residuals and $\bar y$ the mean of `y_true`.

$$
\text{MSE} = \frac{1}{n}\sum_i e_i^2, \qquad \text{RMSE} = \sqrt{\text{MSE}}, \qquad \text{MAE} = \frac{1}{n}\sum_i |e_i|
$$

$$
R^2 = 1 - \frac{SS_{\text{res}}}{SS_{\text{tot}}}, \qquad SS_{\text{res}} = \sum_i e_i^2, \qquad SS_{\text{tot}} = \sum_i (y_i - \bar y)^2
$$

$R^2$ is undefined when `y_true` is constant ($SS_{\text{tot}} = 0$). In that case return `1.0` if $SS_{\text{res}} = 0$ (perfect predictions) and `0.0` otherwise, as scikit-learn does. Detect it as scikit-learn does too, with an exact `SS_tot == 0` check on the value computed above; every constant target in the tests gives exactly `0`. $R^2$ can be negative when the model is worse than predicting the mean.

Return a dict with exactly the keys `"mse"`, `"rmse"`, `"mae"` and `"r2"`, each mapped to a Python `float`.

**Constraints**

- `y_true` and `y_pred` are 1-D float arrays of the same length, `1 <= n <= 10^5`
- entries are finite
