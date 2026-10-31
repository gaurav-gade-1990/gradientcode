## 1. What the problem is really asking

Ridge regression is least squares with a penalty on large weights: you minimize the squared error plus $\alpha\lVert w\rVert^2$. The penalty does two jobs. It **shrinks** weights toward zero, which trades a little bias for much less variance when data is noisy or features are correlated. And it makes the problem **always well-posed**: problem 10 needed a minimum-norm rule for duplicated columns and $n < d$, but with $\alpha > 0$ the minimizer is unique.

The catch in this problem is the **bias**. It is not penalized. If you add $\alpha I$ to the full augmented system from problem 10, you shrink $b$ toward zero too, and your predictions start depending on where the origin of $y$ happens to be. Under the story, the problem is asking you to **separate the unpenalized intercept from the penalized weights**. The standard way is to center the data, solve for $w$, and recover $b$ from the means.

The judge compares `w` and `b` with the reference (`rtol=1e-6`). Penalizing the bias, using the wrong `b`, or scaling `alpha` by `n` all fail.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `X` | float array, shape `(n, d)`, `1 <= n <= 200`, `1 <= d <= 10` | features; columns may be duplicated or constant |
| `y` | float array, shape `(n,)` | targets |
| `alpha` | float `> 0` | penalty strength on $\lVert w\rVert^2$ |
| return | tuple `(w, b)` | `w` shape `(d,)`, `b` a Python float |

Details that are easy to miss:

- **The loss is a sum, not a mean.** Don't multiply `alpha` by `n`. (scikit-learn's `Ridge` uses this same sum convention.)
- **Only `w` is penalized.** Shifting every `y` by 100 must shift `b` by 100 and leave `w` unchanged.
- **`n < d` is fine** ("more features than samples"), and so are duplicated columns. `alpha > 0` makes the system invertible.
- **`b` must be a Python float.**

## 3. The math

The objective is

$$
L(w, b) = \sum_{i=1}^{n}\big(x_i^\top w + b - y_i\big)^2 + \alpha\lVert w\rVert^2 .
$$

**Step 1: eliminate the bias.** For fixed $w$, $L$ is a quadratic in $b$. Set its derivative to zero:

$$
\frac{\partial L}{\partial b} = 2\sum_i \big(x_i^\top w + b - y_i\big) = 0
\quad\Longrightarrow\quad
b = \bar y - \bar x^\top w,
$$

where $\bar x = \frac{1}{n}\sum_i x_i \in \mathbb{R}^d$ and $\bar y = \frac{1}{n}\sum_i y_i$. The penalty has no $b$ in it, so it doesn't appear here. That's the formal meaning of "unpenalized bias".

**Step 2: substitute back.** With that $b$, each residual becomes $x_i^\top w + \bar y - \bar x^\top w - y_i = (x_i - \bar x)^\top w - (y_i - \bar y)$. Define the centered data $X_c = X - \mathbf{1}\bar x^\top$ and $y_c = y - \bar y\mathbf{1}$. The bias has disappeared:

$$
L(w) = \lVert X_c w - y_c\rVert^2 + \alpha\lVert w\rVert^2 .
$$

**Step 3: the gradient in $w$.** Using $\nabla_w\lVert X_c w - y_c\rVert^2 = 2X_c^\top(X_c w - y_c)$ (problem 10 derives it) and $\nabla_w\, \alpha\lVert w\rVert^2 = 2\alpha w$:

$$
\nabla_w L = 2X_c^\top(X_c w - y_c) + 2\alpha w = 0
\quad\Longrightarrow\quad
\big(X_c^\top X_c + \alpha I\big)\, w = X_c^\top y_c .
$$

**Why it's always solvable.** $X_c^\top X_c$ is positive semi-definite: $v^\top X_c^\top X_c v = \lVert X_c v\rVert^2 \ge 0$. Adding $\alpha I$ adds $\alpha\lVert v\rVert^2 > 0$ for every $v \ne 0$, so the matrix is positive definite and invertible. Every eigenvalue moves from $\lambda_k \ge 0$ to $\lambda_k + \alpha > 0$, and the condition number drops from $\lambda_{\max}/\lambda_{\min}$ (possibly infinite) to $(\lambda_{\max} + \alpha)/(\lambda_{\min} + \alpha)$.

**What ridge does, direction by direction.** With the SVD $X_c = U\Sigma V^\top$, the solution is $w = \sum_k \frac{\sigma_k}{\sigma_k^2 + \alpha}\,(u_k^\top y_c)\,v_k$. OLS would use $\frac{1}{\sigma_k}$. So ridge multiplies the OLS component along each direction $v_k$ by $\frac{\sigma_k^2}{\sigma_k^2 + \alpha}$: near 1 for well-determined directions, near 0 for directions the data barely constrains. A constant feature has a zero centered column, so it contributes nothing to $X_c^\top y_c$, and its weight comes out **exactly 0**. Compare problem 10, where the minimum-norm rule gave it part of the intercept.

## 4. Trace an example by hand

**Example 1:** `X = [[1], [2], [3], [4]]`, `y = [3, 5, 7, 9]`, `alpha = 5`.

```python
x_mean, y_mean = [2.5], 6.0
Xc = X - x_mean                    # [[-1.5], [-0.5], [0.5], [1.5]]   (4, 1)
yc = y - y_mean                    # [-3, -1, 1, 3]                    (4,)
Xc.T @ Xc                          # [[5.0]]       = 2.25 + 0.25 + 0.25 + 2.25    (1, 1)
Xc.T @ yc                          # [10.0]                                       (1,)
w = solve([[5 + 5]], [10])         # [1.0]
b = 6 - 2.5 * 1.0                  # 3.5
```

OLS would give `w = 2` (the data lies exactly on `y = 2x + 1`). The penalty halves it: $\sigma^2 / (\sigma^2 + \alpha) = 5 / 10$. The bias then moves to `3.5` so the line still passes through the mean point `(2.5, 6)`.

**Example 2:** `X` shape `(4, 2)`, `alpha = 1`.

```python
x_mean, y_mean = [1, 1], 3.125
Xc.T @ Xc                          # [[2, 1], [1, 2]]     eigenvalues 1 and 3     (2, 2)
Xc.T @ yc                          # [5, 4]                                        (2,)
w = solve([[3, 1], [1, 3]], [5, 4])    # [1.375, 0.875]
b = 3.125 - [1, 1] @ w                 # 0.875
```

**"huge alpha"** ($\alpha = 10^6$) shows the limit: every weight is shrunk to about 0 (`[0, 0, -0, 0.0001]`), and `b = 22.312`, essentially $\bar y$. That's the right limit: with no usable weights, the best constant predictor is the mean. If you penalized the bias too, it would be dragged toward 0 instead.

## 5. Key idea: centering is how you leave the bias out of the penalty

There are two equivalent ways to not penalize $b$:

1. **Center, solve, recover** (the reference): the derivation in section 3. The `d x d` system has no bias row.
2. **Augment with a zero in the penalty**: $A = [X \;\; \mathbf{1}]$ and solve $(A^\top A + P)\theta = A^\top y$ with $P = \operatorname{diag}(\alpha, \dots, \alpha, 0)$. The zero in the bias slot removes the penalty from $b$. This also passes every test.

What doesn't work is $\alpha I$ on the full augmented system. That penalizes $b$, so on Example 1 you get `w = 1.814` instead of `1`. A related mistake is solving on centered data but returning $b = \bar y$. That's only right when $\bar x = 0$; Example 1 gives `6` instead of `3.5`.

## 6. Plan before you code

```
x_mean = column means of X; y_mean = mean of y
Xc = X - x_mean; yc = y - y_mean                    # (n, d), (n,)
w = solve((Xc^T Xc + alpha I), Xc^T yc)             # (d,)
b = y_mean - x_mean . w                             # scalar
return w, float(b)
```

| variant | Example 1 | why |
|---|---|---|
| reference | `w = 1`, `b = 3.5` | correct |
| augmented, $\alpha I$ on bias too | `w = 1.814` | bias penalized |
| centered, `b = y.mean()` | `b = 6` | ignores $\bar x^\top w$ |
| `alpha * n` | `w = 0.4` | mean-loss convention, not this one |
| no centering, `X.T @ X + alpha I` | `w = 2` | the intercept's job leaks into `w` |

## 7. Build it one piece at a time

**Step 1: center.**

```python
x_mean = X.mean(axis=0)        # (d,)
y_mean = y.mean()              # scalar
Xc = X - x_mean                # (n, d) - (d,) -> (n, d)
yc = y - y_mean                # (n,)
```

**Step 2: the regularized normal equations.**

```python
d = X.shape[1]
w = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(d), Xc.T @ yc)   # (d, d) system -> (d,)
```

`alpha * np.eye(d)` adds `alpha` to the **diagonal** only. `Xc.T @ Xc + alpha` (no `eye`) would add it to every entry, which happens to work when `d = 1` and is wrong otherwise. Use `solve`, not `inv`: it factorizes once and is more accurate. Since the matrix is positive definite, `np.linalg.cholesky` would also work.

**Step 3: recover the bias.**

```python
b = y_mean - x_mean @ w        # scalar: the fit passes through (x_mean, y_mean)
return w, float(b)
```

## 8. Full solution

```python
# NumPy gives means, broadcasting and a linear solver
import numpy as np


# minimize sum of squared errors + alpha * ||w||^2 with an unpenalized bias; returns (w, b)
def ridge_regression(X: np.ndarray, y: np.ndarray, alpha: float) -> tuple:
    # per-feature means, (d,): used to center and later to recover the bias
    x_mean = X.mean(axis=0)
    # mean target, a scalar
    y_mean = y.mean()
    # centering removes the bias from the problem, so the penalty can't touch it; (n, d)
    Xc = X - x_mean
    # centered targets, (n,)
    yc = y - y_mean
    # number of weights, for the identity matrix
    d = X.shape[1]
    # (Xc^T Xc + alpha I) w = Xc^T yc; alpha > 0 makes it positive definite, so it is
    # solvable even with duplicated columns or n < d; solve is safer than inv, (d,)
    w = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(d), Xc.T @ yc)
    # the best unpenalized bias for this w makes the fit pass through the mean point
    b = y_mean - x_mean @ w
    # b is a NumPy scalar; the judge wants a Python float
    return w, float(b)
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `([1], 3.5)` | shrinkage by $5/(5+5)$ and the bias recovery |
| Example 2 | `([1.375, 0.875], 0.875)` | the `d x d` system with `eye` on the diagonal only |
| off-center features | `b = 10.0749` | feature means of 3, -2, 0, 5: the bias needs $\bar x^\top w$ |
| tiny alpha | `w = [1.2365, 0.4277, -0.9979, 1.9967]` | near OLS; penalizing the bias barely shows here |
| huge alpha | `w ≈ 0`, `b = 22.312` | `w` shrinks to 0 and `b` tends to $\bar y$, not to 0 |
| duplicated column | `w = [0.1764, -0.2134, 0.1764]` | collinear columns: a unique, equal split |
| more features than samples | shape `(7,)`, `b = -3.3683` | `n = 4 < d = 7` is solvable |
| constant feature | `w[2] = 0` exactly | a zero centered column gets zero weight |

## 10. Complexity

- **Time:** $O(nd)$ to center, $O(nd^2)$ to form $X_c^\top X_c$, and $O(d^3)$ to solve.
- **Memory:** $O(nd)$ for the centered copy, plus $O(d^2)$ for the system.

When $d \gg n$ (text features, genomics), use the dual form: $w = X_c^\top(X_c X_c^\top + \alpha I)^{-1} y_c$ needs an $n \times n$ solve instead of $d \times d$. That identity is the starting point of kernel ridge regression. For choosing $\alpha$, one SVD of $X_c$ gives the solution for every $\alpha$ cheaply (the shrinkage factors in section 3), so cross-validating over a grid costs little more than one fit.

## 11. If you got Wrong Answer

- **`w` is too large and `b` wrong; Example 1 gives `w = 1.814`.** You penalized the bias by adding $\alpha I$ to the full augmented system (`wrong_penalize_bias.py`). With "tiny alpha" or "constant feature" the difference is only in the 6th digit, but it still fails.
- **`w` is right but `b` isn't; Example 1 gives `b = 6`.** You returned `y.mean()` as the bias (`wrong_bias_is_mean_y.py`). Use $\bar y - \bar x^\top w$.
- **Every `w` is too small; Example 1 gives `0.4`.** You multiplied `alpha` by `n`. This problem's loss is a sum.
- **Example 1 passes but Example 2 gives `w[0] = 1.4`.** You wrote `Xc.T @ Xc + alpha` without `np.eye(d)`, adding `alpha` to every entry. With `d = 1` the two are the same.
- **Example 1 gives `w = 2`, the OLS answer.** You skipped centering and solved `X.T @ X + alpha I` with no intercept column. Without an intercept, the penalty has to fight the offset in `y`.

## 12. Follow-ups an interviewer might ask

- *How do you choose `alpha`?* Cross-validation over a log-spaced grid (problem 31, stratified-k-fold). The SVD makes the whole path cheap. Generalized cross-validation gives a closed-form leave-one-out estimate.
- *Why standardize features before ridge?* The penalty treats every weight the same, so a feature in millimetres (small weight) is penalized less than the same feature in metres. Standardize first (problem 7) so the penalty is fair.
- *How does ridge compare to lasso?* Lasso penalizes $\lVert w\rVert_1$, has no closed form, and sets some weights exactly to zero (feature selection). Ridge shrinks smoothly and keeps correlated features together, as in "duplicated column".
- *What's the connection to weight decay?* Gradient descent on the ridge loss adds $2\alpha w$ to the gradient, so each step multiplies $w$ by $(1 - 2\eta\alpha)$ before the data term: that's weight decay (problems 11 and 53).
- *What's the Bayesian view?* Ridge is the MAP estimate under a Gaussian prior $w \sim \mathcal{N}(0, \frac{\sigma^2}{\alpha} I)$ with Gaussian noise of variance $\sigma^2$. Larger $\alpha$ means a tighter prior around zero.
