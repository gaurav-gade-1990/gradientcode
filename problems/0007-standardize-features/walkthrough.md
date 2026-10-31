## 1. What the problem is really asking

Raw features live on wildly different scales: an age in years, an income in dollars, a ratio between 0 and 1. Many models care. Gradient descent zig-zags when one feature is a thousand times larger than another, k-NN distances are dominated by the biggest feature, and regularization penalizes weights unevenly. Standardization rescales each feature to mean 0 and standard deviation 1.

The formula is trivial. What the problem is really asking is the **fit/transform discipline** that every preprocessing step in machine learning follows:

1. **Fit** statistics on the training set only.
2. **Transform** both sets with those same statistics.

That's a protection against **data leakage**. At prediction time you see one example at a time, so there are no "test statistics" to compute. If you standardize the test set with its own mean and std, your evaluation looks at information you won't have in production.

The judge checks both arrays in the returned tuple (`rtol=1e-7`). A test set that was standardized with its own statistics, the wrong std, or no guard for constant columns gives a Wrong Answer.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `X_train` | float array, shape `(n, d)`, `n >= 1` | the only source of `mu` and `sigma` |
| `X_test` | float array, shape `(m, d)`, `m >= 0` | transformed with the training statistics |
| return | tuple `(Z_train, Z_test)` | same shapes as the inputs |

Details that are easy to miss:

- **Population std, `ddof=0`.** Divide by `n`, not `n - 1`. That's `np.std`'s default and what scikit-learn's `StandardScaler` does. (Problem 6 used `n - 1` for covariance; this one doesn't.)
- **Constant columns.** If a training column is constant, $\sigma_j = 0$. Use $\sigma_j = 1$ instead, so that column is only centered. `n = 1` makes **every** column constant ("single training row").
- **`m` can be 0** ("empty test set"). The transform must still return a `(0, d)` array.
- **Don't modify the inputs in place.** Callers often reuse `X_train`, so compute new arrays.

## 3. The math

For each feature $j$, with $n$ training rows:

$$
\mu_j = \frac{1}{n}\sum_{i=1}^{n} X^{\text{tr}}_{ij}, \qquad
\sigma_j = \sqrt{\frac{1}{n}\sum_{i=1}^{n}\big(X^{\text{tr}}_{ij} - \mu_j\big)^2}, \qquad
Z_{ij} = \frac{X_{ij} - \mu_j}{\sigma_j}.
$$

Here $\mu, \sigma \in \mathbb{R}^d$ are vectors, one entry per column, and $X$ is either set.

**Why the training output has mean 0 and std 1.** Average $Z_{ij}$ over the training rows:

$$
\frac{1}{n}\sum_i Z_{ij} = \frac{1}{\sigma_j}\Big(\frac{1}{n}\sum_i X^{\text{tr}}_{ij} - \mu_j\Big) = \frac{\mu_j - \mu_j}{\sigma_j} = 0,
\qquad
\frac{1}{n}\sum_i Z_{ij}^2 = \frac{1}{\sigma_j^2}\cdot\frac{1}{n}\sum_i \big(X^{\text{tr}}_{ij} - \mu_j\big)^2 = \frac{\sigma_j^2}{\sigma_j^2} = 1 .
$$

The test output generally does **not** have mean 0 and std 1. It shouldn't: if the test distribution has shifted, you want to see that.

**Why it helps gradient descent: a derivation.** Take a linear model $\hat y = w x$ with one feature and squared loss $L(w) = \frac{1}{2n}\sum_i (w x_i - y_i)^2$. Its gradient and curvature are

$$
\frac{\partial L}{\partial w} = \frac{1}{n}\sum_i (w x_i - y_i)\, x_i, \qquad
\frac{\partial^2 L}{\partial w^2} = \frac{1}{n}\sum_i x_i^2 .
$$

Scale the feature by $s$ (say, metres to millimetres, $s = 1000$). The curvature becomes $s^2 \cdot \frac{1}{n}\sum x_i^2$, a million times larger. With several features, the loss surface becomes a long, narrow valley: one direction curves $s^2$ times more than another. A learning rate small enough to be stable along the steep direction barely moves along the flat one. After standardizing, each feature has $\frac{1}{n}\sum_i Z_{ij}^2 = 1$, so every diagonal entry of the curvature matrix $\frac{1}{n}Z^\top Z$ is exactly 1. That's the motivation for problem 11 (linear-regression-gradient-descent) and for batch norm and layer norm (problems 39–41), which apply this same transform inside a network.

**The constant-column guard.** If $\sigma_j = 0$, every training value equals $\mu_j$, and $Z_{ij} = 0/0$ in training. Replacing $\sigma_j$ by 1 gives $Z_{ij} = X_{ij} - \mu_j$: zero in training, and the raw offset in test. A test value of `12` on a training constant of `10` maps to `2`, a finite and meaningful number.

## 4. Trace an example by hand

**Example 1:** `X_train = [[1, 10], [3, 10]]`, `X_test = [[2, 12], [5, 10]]`, both shape `(2, 2)`.

```python
mu = X_train.mean(axis=0)                   # [2., 10.]           (2,)
sigma = X_train.std(axis=0)                 # [1., 0.]            (2,)  column 2 is constant
sigma = np.where(sigma == 0, 1.0, sigma)    # [1., 1.]            (2,)
(X_train - mu) / sigma                      # [[-1, 0], [1, 0]]   (2, 2)
(X_test - mu) / sigma                       # [[0, 2], [3, 0]]    (2, 2)
```

Column 1: mean 2, std `sqrt(((1-2)^2 + (3-2)^2) / 2) = 1`. Test value 5 maps to `(5 - 2) / 1 = 3`. Column 2 is constant at 10, so it's only centered: 12 maps to 2.

**Example 2:** `X_train = [[0], [2], [4], [6]]`, `X_test = [[8]]`. Mean 3, population std `sqrt((9 + 1 + 1 + 9) / 4) = sqrt(5) = 2.2361`. Training gives `[-1.3416, -0.4472, 0.4472, 1.3416]`. The test value is `(8 - 3) / sqrt(5) = 2.2361`. If you standardized the test set on its own, its single value would be `(8 - 8) / 1 = 0`.

**"different scales and shifts"** shows why test outputs look odd. Column 3 of the training data is about `3.0` with std about `0.01`. The test data was generated around `4.0`, so its standardized values are around `100` (for example `103.4904`). That's correct: the test column is 100 training standard deviations away. A fit-on-test version would hide that drift entirely.

## 5. Key idea: broadcasting `(d,)` statistics over rows

`X_train.mean(axis=0)` reduces over rows and has shape `(d,)`. Subtracting it from an `(n, d)` array right-aligns `(d,)` with the last axis, so each column gets its own mean subtracted. The same `(d,)` vectors work for `X_test` of shape `(m, d)`, because only the trailing `d` has to match.

That's also why `m = 0` needs no special case: `(0, d) - (d,)` is a valid broadcast that produces `(0, d)`.

Here `keepdims` isn't needed (the reduced axis is the leading one, so the right-aligned broadcast is the one you want). It would be needed if you standardized rows instead, as layer norm does (problem 41).

## 6. Plan before you code

```
mu = column means of X_train                     # (d,)
sigma = column population stds of X_train        # (d,)
replace zeros in sigma with 1                     # constant columns are only centered
return ((X_train - mu) / sigma, (X_test - mu) / sigma)   # new arrays; inputs untouched
```

| choice | Example 1 result |
|---|---|
| fit on train, `ddof=0`, guard | `Z_train[0, 0] = -1`, `Z_test = [[0, 2], [3, 0]]` (correct) |
| `ddof=1` | `Z_train[0, 0] = -0.7071` |
| fit on test | `Z_test[0, 0] = -1` instead of `0` |
| fit on train and test combined | `Z_train[0, 0] = -1.1832` |
| `sigma + 1e-12` instead of a guard | `Z_test[0, 1] = 2e+12` instead of `2` |

## 7. Build it one piece at a time

**Step 1: fit the statistics on the training set.**

```python
mu = X_train.mean(axis=0)      # (n, d) -> (d,)
sigma = X_train.std(axis=0)    # (n, d) -> (d,), population std (ddof=0)
```

**Step 2: guard constant columns.**

```python
sigma = np.where(sigma == 0, 1.0, sigma)    # (d,)
```

`np.where` returns a new array, so the original statistics aren't mutated. An exact `== 0` works on these tests because their constant columns hold values like `3.0`, whose std comes out exactly `0.0`. Be aware that a constant column of `0.1` can give a std of about `1e-17` instead, because `0.1` isn't exactly representable. scikit-learn guards with a small relative threshold for that reason. Don't swap in a fixed absolute cutoff like `sigma < 1e-8`, though: the statement replaces $\sigma_j$ only when it is exactly 0, and the hidden case "tiny but nonzero spread" has a column `[0, 2e-9]` with a real std of `1e-9`. It must scale to `[-1, 1]`, with test values `[1e-9, 4e-9]` mapping to `[0, 3]`.

**Step 3: transform both sets with the same statistics.**

```python
return (X_train - mu) / sigma, (X_test - mu) / sigma    # (n, d) and (m, d)
```

The subtraction creates new arrays, so the inputs are untouched. Writing `X_train -= mu` would modify the caller's array.

## 8. Full solution

```python
# NumPy gives column means and stds and broadcasting
import numpy as np


# fit on X_train (n, d), transform X_train and X_test (m, d); returns (Z_train, Z_test)
def standardize(X_train: np.ndarray, X_test: np.ndarray) -> tuple:
    # per-feature mean, from the training rows only so the test set can't leak in; (d,)
    mu = X_train.mean(axis=0)
    # per-feature population std (ddof=0, like StandardScaler); (d,)
    sigma = X_train.std(axis=0)
    # a constant column has std 0; divide it by 1 so it is only centered instead of 0/0
    sigma = np.where(sigma == 0, 1.0, sigma)
    # apply the same training statistics to both sets; (d,) broadcasts over the rows,
    # and the subtraction makes new arrays so the inputs are not modified
    return (X_train - mu) / sigma, (X_test - mu) / sigma
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `Z_train = [[-1, 0], [1, 0]]`, `Z_test = [[0, 2], [3, 0]]` | train-only stats and the constant-column guard |
| Example 2 | `Z_test = [[2.2361]]` | population std $\sqrt{5}$; the test row uses training stats |
| different scales and shifts | `Z_test` column 3 around `100`, e.g. `103.4904` | per-column stats on very different scales; drift stays visible |
| constant column in train | `Z_test` column 2 is `[0, 1, -1, 0, 7]` | guard: test values are only centered |
| tiny but nonzero spread | `Z_train = [[-1, -1], [1, 1]]`, `Z_test = [[0, 0], [3, 3]]` | only an exact zero std is replaced; std `1e-9` still divides |
| single training row | `Z_train = [[0, 0, 0]]`, `Z_test = [[-1, 2, -3], [0, 0, 1]]` | `n = 1`: every std is 0, so everything is only centered |
| empty test set | `Z_test` has shape `(0, 3)` | `m = 0` through broadcasting |
| test equals train | `Z_test` equals `Z_train` | same stats applied twice give identical outputs |
| larger | shapes `(200, 10)` and `(50, 10)` | skewed (exponential) data, test scaled by 3 |

## 10. Complexity

With `n` training rows, `m` test rows and `d` features:

- **Time:** $O(nd)$ to fit, plus $O((n + m)d)$ to transform.
- **Memory:** $O(d)$ for the statistics, plus $O((n + m)d)$ for the outputs.

In production the fit happens once, offline, and $\mu$ and $\sigma$ are saved **with the model**. At serving time you apply the stored vectors to each request. Recomputing them from serving traffic, or forgetting to apply them at all, is one form of train/serve skew (problem 150), and it fails silently: the model still returns numbers, just worse ones.

## 11. If you got Wrong Answer

- **The test output is wrong in the first element but training is fine; Example 2 gives `0` instead of `2.2361`.** You standardized the test set with its own statistics (`wrong_fit_on_test.py`). It passes "test equals train" and "empty test set", where the two are indistinguishable.
- **Every training value is a bit too small in magnitude; Example 1 gives `-0.7071` instead of `-1`.** You used `ddof=1` (`wrong_ddof1.py`). It passes "single training row" only because that version special-cases `n = 1`.
- **A huge value like `2e+12` in the test output.** You added a tiny epsilon to `sigma` instead of guarding (`wrong_no_constant_guard.py`). Training values of a constant column are `0 / 1e-12 = 0`, so training looks fine, but any test value that differs from the constant explodes. It fails Example 1, "constant column in train" and "single training row".
- **Column 2 of "tiny but nonzero spread" comes out as `[-0, 0]` and `[0, 0]`.** You guarded with a threshold such as `sigma < 1e-8` (`wrong_threshold_guard.py`), so a column with std `1e-9` was only centered. Replace sigma only where it is exactly `0`.
- **Every training value is off, Example 1 gives `-1.1832`.** You fit on train and test stacked together.
- **`nan` in training output.** No guard at all: a constant column gives `0 / 0`.

## 12. Follow-ups an interviewer might ask

- *Why not fit on all the data you have?* Any statistic computed from the test set lets test information shape the model's inputs, so the test score is optimistic. In cross-validation, refit the scaler on each training fold (problem 31, stratified-k-fold).
- *What about outliers?* One huge value inflates $\sigma$ and squashes everything else. A robust scaler uses the median and interquartile range instead.
- *How does this relate to batch norm and layer norm?* Batch norm standardizes each feature over the batch during training and uses running averages at inference: the same fit/transform split (problems 39, 40). Layer norm standardizes each **row** over its features, so it has no train/test difference (problem 41).
- *Do tree models need this?* No. A split threshold is invariant to monotone rescaling of a feature (problem 20, gini-impurity-best-split).
- *How would you invert it?* $X = Z \sigma + \mu$, using the stored vectors. You need that to turn standardized predictions back into the original units.
