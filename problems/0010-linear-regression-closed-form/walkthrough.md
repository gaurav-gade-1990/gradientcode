## 1. What the problem is really asking

Fit a straight line (or a flat hyperplane, with several features) through data by minimizing squared error, and do it **in closed form**: solve a linear system once instead of iterating. That's ordinary least squares, the baseline every regression model gets compared against.

Under the story there are two things to get right:

1. **The intercept.** The model is $x^\top w + b$, so you fold $b$ into the weights by appending a column of ones to `X`.
2. **Rank deficiency.** When columns are duplicated, a feature is constant, or there are fewer rows than unknowns, infinitely many $\theta$ achieve the minimum error. The problem picks one: the solution with the **smallest norm**. Inverting $A^\top A$ either crashes or returns a different minimizer in those cases.

The judge compares `w` and `b` with the reference (`rtol=1e-6`, `atol=1e-8`). Three of the eight tests are rank-deficient, so the minimum-norm rule is the heart of the problem.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `X` | float array, shape `(n, d)`, `1 <= n <= 200`, `1 <= d <= 10` | the features; augmented with a ones column |
| `y` | float array, shape `(n,)` | the targets |
| return | tuple `(w, b)` | `w` has shape `(d,)`, `b` is a Python `float` |

Details that are easy to miss:

- **Put the ones column last.** Then `theta[:-1]` is `w` and `theta[-1]` is `b`. Putting it first and splitting as if it were last swaps the bias into `w[0]`.
- **The minimum norm covers `w` and `b` together.** It's $\lVert [w; b] \rVert$, not $\lVert w \rVert$ alone. That decides how the intercept is split when a feature is constant.
- **`n` can be smaller than `d + 1`** ("underdetermined": 3 rows, 6 unknowns). Then the data can be fit exactly in many ways.
- **`b` must be a Python float.** `float(theta[-1])` converts the NumPy scalar.

## 3. The math

Let $A = [X \;\; \mathbf{1}] \in \mathbb{R}^{n \times (d+1)}$ and $\theta = [w; b] \in \mathbb{R}^{d+1}$, so the predictions are $A\theta$. The loss is

$$
L(\theta) = \lVert A\theta - y \rVert^2 = (A\theta - y)^\top (A\theta - y) = \theta^\top A^\top A\, \theta - 2\, y^\top A\, \theta + y^\top y .
$$

**Deriving the gradient.** Use two matrix-calculus rules: $\nabla_\theta (c^\top \theta) = c$, and for symmetric $M$, $\nabla_\theta (\theta^\top M \theta) = 2M\theta$. Here $M = A^\top A$ (symmetric) and $c = A^\top y$:

$$
\nabla_\theta L = 2A^\top A\,\theta - 2A^\top y = 2A^\top (A\theta - y).
$$

Read the last form: the gradient is $A^\top$ times the residual $r = A\theta - y$. Problem 11 (linear-regression-gradient-descent) steps along exactly this.

**The normal equations.** $L$ is a convex quadratic (its Hessian $2A^\top A$ is positive semi-definite), so every point with zero gradient is a global minimum:

$$
A^\top A\, \theta = A^\top y .
$$

Equivalently $A^\top r = 0$: at the optimum the residual is orthogonal to every column of $A$. Since the ones column is one of them, $\sum_i r_i = 0$: OLS residuals with an intercept always average to zero.

**When the solution is unique.** If $A$ has full column rank ($\operatorname{rank} A = d + 1$), $A^\top A$ is invertible and $\theta = (A^\top A)^{-1} A^\top y$. If not, $A$ has a null space: some $v \ne 0$ with $Av = 0$. Then $\theta + tv$ gives the same predictions, hence the same loss, for every $t$. The minimizers form a line, plane or more.

**The minimum-norm solution.** Among all minimizers, the smallest $\lVert\theta\rVert$ is the one with no component in the null space of $A$. With the SVD $A = U \Sigma V^\top$, it is

$$
\theta^\star = A^{+} y = V \Sigma^{+} U^\top y,
$$

where $\Sigma^{+}$ inverts the nonzero singular values and leaves the zeros at zero. `np.linalg.lstsq` and `np.linalg.pinv` both compute this.

**What minimum norm does to a constant feature.** Suppose column $j$ is the constant 3. Then $3w_j + b$ acts as one combined intercept $K$, and the data fixes only $K$. Minimizing $w_j^2 + b^2$ subject to $3w_j + b = K$ (Lagrange: $(w_j, b) \propto (3, 1)$) gives $w_j = 3K/10$ and $b = K/10$. In "constant feature", $K = 0.5730$, and indeed $w_j = 0.1719$, $b = 0.0573$, a ratio of exactly 3. A duplicated column splits its weight equally for the same reason.

**Numerical stability.** Forming $A^\top A$ squares the condition number: on Example 2, $\kappa(A) = 5.30$ but $\kappa(A^\top A) = 28.07$. On ill-conditioned data that's the difference between losing a few digits and losing all of them. `lstsq` works on $A$ directly through the SVD, so it never forms $A^\top A$.

## 4. Trace an example by hand

**Example 2:** `X` has shape `(4, 2)`, `y = [1, 2, 2.5, 4]`.

```python
A = np.hstack([X, np.ones((4, 1))])
# [[0, 1, 1],
#  [1, 0, 1],
#  [1, 1, 1],
#  [2, 1, 1]]                       (4, 3)
A.T @ A                             # [[6, 3, 4], [3, 3, 3], [4, 3, 4]]     (3, 3)
A.T @ y                             # [12.5, 7.5, 9.5]                      (3,)
theta                               # [1.5, 0.5, 0.5]                       (3,)
# w = theta[:-1] = [1.5, 0.5],  b = theta[-1] = 0.5
```

Check the residuals: $1.5 \cdot 0 + 0.5 \cdot 1 + 0.5 = 1$, $1.5 + 0.5 = 2$, $1.5 + 0.5 + 0.5 = 2.5$, $3 + 0.5 + 0.5 = 4$. All four points sit exactly on the plane (the residuals are about $10^{-16}$). Four points and three unknowns don't force a nonzero error; these happen to be coplanar.

**"duplicated column"**: column 3 equals column 1, and `y` was built as $1 \cdot x_1 - 2x_2 + 1 \cdot x_3 + 0.5$ plus noise. Only $w_1 + w_3$ is identifiable; the data says it's about `1.9954`. The minimum-norm rule splits it equally: `w = [0.9977, -2.0092, 0.9977]`, `b = 0.5000`. `inv(A.T @ A)` raises "Singular matrix" here.

**"underdetermined"**: `A` is `(3, 6)`, rank 3. Every residual can be made zero, and lstsq returns the exact fit with the smallest norm, $\lVert\theta\rVert = 0.5458$.

## 5. Key idea: let `lstsq` handle every rank

You could special-case: solve the normal equations when $A^\top A$ is invertible, use `pinv` otherwise. But deciding "invertible" in floating point is itself a judgment call. `np.linalg.lstsq(A, y, rcond=None)` makes it for you: it computes the SVD, treats singular values below a machine-precision threshold as zero (that's what `rcond=None` selects), and returns $A^+ y$. One call is correct for full-rank, rank-deficient and underdetermined inputs, and more accurate than the normal equations on all of them.

## 6. Plan before you code

```
A = [X | 1]                                  # (n, d + 1), ones column last
theta = minimum-norm least-squares solution  # (d + 1,), via lstsq
return theta[:-1], float(theta[-1])          # w (d,), b float
```

| method | full rank | dependent columns | `n < d + 1` |
|---|---|---|---|
| `lstsq` or `pinv` | correct | minimum norm | minimum norm |
| `inv(A.T @ A) @ A.T @ y` | correct (less accurate) | crash or wrong minimizer | wrong minimizer |
| `solve(A.T @ A, A.T @ y)` | correct | crash or wrong minimizer | wrong minimizer |
| center, solve for `w`, then `b = ȳ - x̄ᵀw` | correct | minimizes $\lVert w\rVert$ only | wrong |

## 7. Build it one piece at a time

**Step 1: augment with the bias column.**

```python
A = np.hstack([X, np.ones((X.shape[0], 1))])   # (n, d) | (n, 1) -> (n, d + 1)
```

`np.ones((n, 1))` must be 2-D for `hstack` to place it as a column.

**Step 2: solve in the least-squares sense.**

```python
theta, *_ = np.linalg.lstsq(A, y, rcond=None)   # (d + 1,)
```

`lstsq` returns four things: the solution, the residual sum of squares, the rank and the singular values. `theta, *_ =` keeps the first. `rcond=None` uses the machine-precision cutoff and silences an old deprecation warning.

**Step 3: split.**

```python
return theta[:-1], float(theta[-1])             # w: (d,), b: float
```

## 8. Full solution

```python
# NumPy gives hstack and an SVD-based least-squares solver
import numpy as np


# X: (n, d), y: (n,); returns (w, b) minimizing squared error, minimum norm if not unique
def fit_linear_regression(X: np.ndarray, y: np.ndarray) -> tuple:
    # append a ones column so the bias is just one more weight: A is (n, d + 1)
    A = np.hstack([X, np.ones((X.shape[0], 1))])
    # SVD-based least squares: never forms A^T A, and returns the minimum-norm theta
    # when columns are dependent or n < d + 1; keep only the solution, (d + 1,)
    theta, *_ = np.linalg.lstsq(A, y, rcond=None)
    # the last entry is the bias (ones column last); return it as a Python float
    return theta[:-1], float(theta[-1])
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `w = [2]`, `b = 1` | exact line `y = 2x + 1`; the bias column |
| Example 2 | `w = [1.5, 0.5]`, `b = 0.5` | two features, solved jointly |
| single feature noisy | `w = [-0.2951]`, `b = -0.4274` | a noisy fit where the residual isn't zero |
| many samples | `b = 2.4987`, close to the true 2.5 | the general full-rank case |
| large intercept | `b = 99.9162` | dropping the bias column is badly wrong (`w[0]` becomes `-24.1`) |
| duplicated column | `w = [0.9977, -2.0092, 0.9977]` | rank deficiency: equal split; `inv` crashes |
| constant feature | `w[2] = 0.1719`, `b = 0.0573` | a feature collinear with the bias, split 3 : 1 |
| underdetermined | `w[0] = 0.0977`, `b = -0.1686` | `n < d + 1`: the minimum-norm exact fit |

## 10. Complexity

With $p = d + 1$ unknowns:

- **Time:** $O(np^2)$ for the SVD-based solve (assuming $n \ge p$). The normal equations are also $O(np^2)$ to form plus $O(p^3)$ to solve, slightly cheaper but less accurate.
- **Memory:** $O(np)$ for `A`.

That's fine up to thousands of features. Beyond that, $O(np^2)$ and the $p \times p$ systems get expensive, and you switch to iterative methods: gradient descent (problem 11), or conjugate gradients on the normal equations, which only need products with $A$ and $A^\top$. Adding a ridge penalty $\lambda I$ (problem 12) also makes the system always invertible and removes the rank question.

## 11. If you got Wrong Answer

- **Runtime Error "Singular matrix" on "duplicated column".** You inverted or solved $A^\top A$ (`wrong_inverse_normal_equation.py`). It also gives a different (not minimum-norm) answer on "constant feature" and "underdetermined" without crashing, and passes the full-rank cases.
- **Every case wrong; Example 1 gives `w = [2.3333]`, "large intercept" gives `w[0] = -24.1`.** No bias column (`wrong_no_bias.py`): the fit is forced through the origin.
- **`w[0]` equals the expected `b` (Example 1 gives `w = [1]`).** You put the ones column first but split as if it were last.
- **Only "constant feature" and "underdetermined" fail; `w[2]` is `0` instead of `0.1719`.** You centered the data and solved for `w` alone, then set `b = ȳ - x̄ᵀw`. That minimizes $\lVert w\rVert$, not $\lVert [w; b]\rVert$.
- **"expected a number, got ndarray" for `b`.** Return `float(theta[-1])`, not `theta[-1:]`.

## 12. Follow-ups an interviewer might ask

- *How would you solve this without a closed form?* Gradient descent on $L$ using $\nabla L = 2A^\top(A\theta - y)$ (problem 11). Started from zero, it converges to the same minimum-norm solution, because its updates always lie in the row space of $A$.
- *What does ridge regression change?* Minimize $\lVert A\theta - y\rVert^2 + \lambda\lVert w\rVert^2$. The normal equations get $+\lambda I$ (usually without penalizing $b$), which is invertible for any $\lambda > 0$ (problem 12, ridge-regression).
- *Why not always use the normal equations?* They square the condition number. With $\kappa(A) = 10^8$, $\kappa(A^\top A) = 10^{16}$, and float64 has about 16 digits. QR or SVD works on $A$ directly.
- *How do you tell if the fit is any good?* Compare MSE and $R^2$ on held-out data (problem 30, regression-metrics). The residuals average to zero by construction, so look at their spread and patterns instead.
- *What if the features have wildly different scales?* The closed form doesn't care in exact arithmetic, but conditioning does, and gradient descent cares a lot. Standardize first (problem 7).
