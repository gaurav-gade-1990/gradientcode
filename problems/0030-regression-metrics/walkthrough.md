## 1. What the problem is really asking

Regression models are judged on their residuals, $e_i = y_i - \hat y_i$. The four standard summaries answer different questions:

- **MSE**: the average squared miss. It's the quantity least squares minimizes (problem 10, linear-regression-closed-form).
- **RMSE**: the square root of MSE, back in the units of $y$.
- **MAE**: the average absolute miss, less sensitive to a few large errors.
- **$R^2$**: how much better you are than the dumbest reasonable model, one that always predicts the mean of the targets.

Under the story, this is **one residual vector and four reductions over it**, plus one edge case: $R^2$ divides by the spread of the targets, which is zero when every target is the same. The spec says exactly what to return then.

The judge compares a dict with exactly the keys `"mse"`, `"rmse"`, `"mae"` and `"r2"`, each to `rtol = 1e-9`. The traps are an $R^2$ baseline centered on the wrong mean, a division by zero for constant targets, and an RMSE that's secretly MAE.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `y_true` | `(n,)` float | targets | residuals, and the baseline mean $\bar y$ |
| `y_pred` | `(n,)` float | predictions | residuals only |
| return | `dict` of four floats | `mse`, `rmse`, `mae`, `r2` | every key compared to `rtol = 1e-9` |

Three details are easy to miss:

- **$\bar y$ is the mean of `y_true`, not `y_pred`.** The baseline model predicts the average target.
- **$R^2$ can be negative.** Example 2 predicts the targets in reverse and scores $-3$. Don't clip it to $[0, 1]$.
- **A single sample is a constant target.** With $n = 1$, $y_1 = \bar y$, so $SS_{\text{tot}} = 0$. "single sample" hits the special case even though nothing looks constant.

## 3. The math

**The three error metrics.**

$$
\text{MSE} = \frac{1}{n}\sum_i e_i^2, \qquad
\text{RMSE} = \sqrt{\text{MSE}}, \qquad
\text{MAE} = \frac{1}{n}\sum_i |e_i| .
$$

**RMSE is never smaller than MAE.** By Jensen's inequality (or Cauchy-Schwarz), the mean of $|e_i|$ is at most the root of the mean of $|e_i|^2$:

$$
\text{MAE} = \frac{1}{n}\sum_i |e_i| \le \sqrt{\frac{1}{n}\sum_i e_i^2} = \text{RMSE},
$$

with equality only when every $|e_i|$ is the same, as in "biased predictions" (every residual is $-2$, so both are 2). The gap between them is a quick outlier signal: one big miss raises RMSE much more than MAE. Writing RMSE as `np.mean(np.sqrt(e**2))` computes MAE, because $\sqrt{e^2} = |e|$; the square root has to go *outside* the mean.

**Why the baseline is the mean.** Among all constant predictions $c$, which one has the smallest squared error? Differentiate $S(c) = \sum_i (y_i - c)^2$:

$$
S'(c) = -2 \sum_i (y_i - c) = 0 \;\Longrightarrow\; c = \frac{1}{n}\sum_i y_i = \bar y .
$$

So $SS_{\text{tot}} = S(\bar y) = \sum_i (y_i - \bar y)^2$ is the squared error of the best constant model, and

$$
R^2 = 1 - \frac{SS_{\text{res}}}{SS_{\text{tot}}}
$$

is the fraction of that error your model removes. $R^2 = 1$ is perfect, $R^2 = 0$ is no better than predicting $\bar y$ ("predict the mean"), and $R^2 < 0$ is worse than that. Nothing here is a square, so the name is misleading: for least-squares fits *with an intercept, evaluated on the training data*, $R^2$ equals the squared correlation between $y$ and $\hat y$ and lies in $[0, 1]$. For arbitrary predictions, it doesn't.

**The constant-target case.** If every $y_i$ is the same, $SS_{\text{tot}} = 0$ and the ratio is $0/0$ or $x/0$. NumPy would return `nan` or `-inf` with a warning. Following scikit-learn, return `1.0` if the predictions are perfect ($SS_{\text{res}} = 0$) and `0.0` otherwise.

**A floating-point caveat.** The check `ss_tot == 0` relies on `y_true.mean()` coming out bit-for-bit equal to the constant. It does for values like `5.0` (the tests' constant), but not for every float: for `np.full(3, 0.1)`, $SS_{\text{tot}}$ comes out as about $5.8 \times 10^{-34}$, not 0, and an imperfect prediction would then get a hugely negative $R^2$. scikit-learn's own check is also an exact comparison with zero, so the spec matches it; in your own code, a relative tolerance is safer.

## 4. Trace an example by hand

**Example 1.** `y_true = [3, -0.5, 2, 7]`, `y_pred = [2.5, 0, 2, 8]`.

| $i$ | $y$ | $\hat y$ | $e$ | $e^2$ | $\lvert e\rvert$ | $(y - \bar y)^2$ |
|---|---|---|---|---|---|---|
| 0 | 3 | 2.5 | 0.5 | 0.25 | 0.5 | 0.0156 |
| 1 | -0.5 | 0 | -0.5 | 0.25 | 0.5 | 11.3906 |
| 2 | 2 | 2 | 0 | 0 | 0 | 0.7656 |
| 3 | 7 | 8 | -1 | 1 | 1 | 17.0156 |
| **sum** | | | | **1.5** | **2** | **29.1875** |

With $\bar y = 11.5 / 4 = 2.875$:

- $\text{MSE} = 1.5 / 4 = 0.375$, $\text{RMSE} = \sqrt{0.375} = 0.612372$, $\text{MAE} = 2 / 4 = 0.5$,
- $R^2 = 1 - 1.5 / 29.1875 = 0.948608$.

Centering on the mean of the predictions instead ($\bar{\hat y} = 3.125$) gives $SS_{\text{tot}} = 29.4375$ and $R^2 = 0.949045$, close enough to look right and far outside `rtol = 1e-9`.

**The hidden "biased predictions" case** shows why $R^2$ can go negative while the error metrics look modest. `y_true = [0, 1, 2, 3, 4]`, `y_pred = [2, 3, 4, 5, 6]`: every prediction is 2 too high. $\text{MSE} = 4$, $\text{RMSE} = \text{MAE} = 2$. $SS_{\text{res}} = 20$, $SS_{\text{tot}} = 10$, so $R^2 = 1 - 2 = -1$. The predictions have the right shape (perfect correlation with the targets), but a constant offset makes them worse than predicting `2` for everything. With the wrong baseline (centered on the predictions' mean, 4) you'd get $SS_{\text{tot}} = 30$ and $R^2 = 0.3333$.

## 5. Plan before you code

```
e = y_true - y_pred                          # (n,)
mse = mean(e^2); rmse = sqrt(mse); mae = mean(|e|)
ss_res = sum(e^2)
ss_tot = sum((y_true - mean(y_true))^2)
if ss_tot == 0: r2 = 1.0 if ss_res == 0 else 0.0
else:           r2 = 1 - ss_res / ss_tot
return the four values as Python floats in a dict
```

| situation | $SS_{\text{tot}}$ | $SS_{\text{res}}$ | `r2` |
|---|---|---|---|
| ordinary | `> 0` | any | `1 - ss_res / ss_tot` |
| constant target, perfect | `0` | `0` | `1.0` |
| constant target, off (or $n = 1$, off) | `0` | `> 0` | `0.0` |

## 6. Build it one piece at a time

**Step 1: residuals and the error metrics.**

```python
e = y_true - y_pred                          # (n,)
mse = float(np.mean(e ** 2))
```

Both inputs are `(n,)`, so the subtraction is elementwise. Computing `e` once and reusing it keeps the four metrics consistent with each other.

**Step 2: the two sums of squares.**

```python
ss_res = float(np.sum(e ** 2))                          # n * mse
ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))   # (n,) - scalar broadcasts
```

`y_true.mean()` is a scalar, and subtracting it broadcasts across all `n` entries. $SS_{\text{res}}$ is just $n \cdot \text{MSE}$; computing it as its own sum avoids a multiply that could differ in the last bit.

**Step 3: $R^2$ with the special case first.**

```python
if ss_tot == 0:
    r2 = 1.0 if ss_res == 0 else 0.0
else:
    r2 = 1.0 - ss_res / ss_tot
```

Checking first means the division never sees a zero denominator, so there's no warning and no `nan`.

**Step 4: the dict.** Every value goes through `float(...)` so the dict holds plain Python floats, not NumPy scalars, and RMSE is `np.sqrt` of the already-computed MSE.

## 7. Full solution

```python
import numpy as np  # vectorized reductions over the residual vector


# MSE, RMSE, MAE and R^2 of predictions against targets, as a dict of Python floats
def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    e = y_true - y_pred  # (n,) residuals, computed once and shared by every metric
    mse = float(np.mean(e ** 2))  # mean squared error
    ss_res = float(np.sum(e ** 2))  # residual sum of squares, the numerator of R^2's ratio
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))  # error of the best constant model, which predicts mean(y_true)
    if ss_tot == 0:  # constant targets (or n = 1): R^2's ratio is undefined
        r2 = 1.0 if ss_res == 0 else 0.0  # scikit-learn's convention: 1 if perfect, else 0
    else:  # the ordinary case
        r2 = 1.0 - ss_res / ss_tot  # share of the baseline's error removed; negative if worse than the mean
    # RMSE is the root of the MEAN of squares (not the mean of roots, which would be MAE)
    return {"mse": mse, "rmse": float(np.sqrt(mse)), "mae": float(np.mean(np.abs(e))), "r2": r2}
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `mse 0.375, rmse 0.612372, mae 0.5, r2 0.948608` | the four formulas; $SS_{\text{tot}} = 29.1875$ around $\bar y = 2.875$ |
| Example 2 | `r2 -3` | worse than the mean: $SS_{\text{res}} = 8$, $SS_{\text{tot}} = 2$ |
| perfect | all errors 0, `r2 1` | the ordinary branch with $SS_{\text{res}} = 0$ |
| constant target, perfect | `r2 1` | $SS_{\text{tot}} = SS_{\text{res}} = 0$ |
| constant target, off | `r2 0`, `rmse 0.75`, `mae 0.625` | $SS_{\text{tot}} = 0$, $SS_{\text{res}} > 0$ |
| predict the mean | `r2 0` | predictions equal $\bar y = 3$: exactly the baseline |
| single sample | `mse 9, rmse 3, mae 3, r2 0` | $n = 1$ means $SS_{\text{tot}} = 0$ |
| biased predictions | `rmse 2, mae 2, r2 -1` | a constant offset; RMSE equals MAE when all errors are equal |
| noisy line | `rmse 1.04489, mae 0.8222, r2 0.983045` | 100 points around $y = 3x + 2$ with unit noise |

## 9. Complexity

With `n` samples:

- **Time:** $O(n)$: one subtraction and a handful of reductions.
- **Memory:** $O(n)$ for the residuals and temporaries.

All four metrics can be computed in a streaming or distributed setting from five running totals: $n$, $\sum e^2$, $\sum |e|$, $\sum y$ and $\sum y^2$, since $SS_{\text{tot}} = \sum y^2 - (\sum y)^2 / n$. That last formula is numerically fragile when the targets are large and nearly constant (catastrophic cancellation); Welford's algorithm, or merging per-shard means and centered sums, avoids it.

## 10. If you got Wrong Answer

- **`r2` is `nan` or `-inf` on the constant-target cases and on "single sample".** You divided by $SS_{\text{tot}}$ without the special case (`wrong_no_constant_case.py`). "constant target, perfect" gives `nan` ($0/0$) and "constant target, off" gives `-inf`.
- **`r2` is close but wrong on Example 1 (`0.949045`), and "biased predictions" gives `0.333333`.** You centered $SS_{\text{tot}}$ on the mean of the predictions (`wrong_r2_pred_mean.py`). The baseline is the mean of `y_true`. On "constant target, off" this bug gives `-35`.
- **`rmse` equals `mae` (Example 1 gives `0.5`).** You took the mean of $\sqrt{e^2}$ instead of the square root of the mean (`wrong_rmse_of_abs.py`). The cases where every $|e_i|$ is equal ("biased predictions", "single sample") pass by coincidence.
- **The checker rejects your output type.** Return a dict with exactly the four keys, each a float.
- **`r2` was clipped to 0.** Example 2 expects $-3$. Don't clip.

## 11. Follow-ups an interviewer might ask

- *When would you prefer MAE to RMSE?* When outliers shouldn't dominate, or when the business cost of an error is linear in its size. MAE is minimized by the median, RMSE by the mean, so they also imply different "best" predictions.
- *What's adjusted $R^2$?* $1 - (1 - R^2)\frac{n - 1}{n - p - 1}$ for $p$ features. Plain $R^2$ never drops when you add a feature on training data; the adjustment penalizes extra features. Better still, report $R^2$ on held-out data, where it can go negative.
- *How do you compare errors across targets with different scales?* Use a scale-free metric: MAPE (undefined at $y = 0$), normalized RMSE (RMSE divided by the targets' standard deviation, which is $\sqrt{1 - R^2}$ up to the $n$ vs $n-1$ factor), or $R^2$ itself.
- *Why might the `ss_tot == 0` check misfire?* Floating-point means aren't always exact: a constant target of `0.1` repeated three times gives $SS_{\text{tot}} \approx 5.8 \times 10^{-34}$, not 0. Compare against a tolerance relative to the targets' magnitude in production code.
- *How do these metrics relate to training?* Least squares minimizes MSE directly; ridge adds a penalty to it (problem 12, ridge-regression). Gradient descent on MSE (problem 11, linear-regression-gradient-descent) uses the residuals $e$ computed here, since $\nabla_w \text{MSE} = -\frac{2}{n} X^\top e$.
