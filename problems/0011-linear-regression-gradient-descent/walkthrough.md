## 1. What the problem is really asking

Problem 10 solved linear regression in one shot with a linear-algebra solver. This one solves the same model the way every neural network is trained: start from zero, compute the gradient of the loss, take a small step downhill, repeat.

Under the story, this is an **iterative update with a fixed recipe**, and the judge checks the recipe, not just the destination. Your `(w, b)` after exactly `n_iters` steps is compared with the reference to `rtol=1e-6`. Several tests stop after 1, 3 or 10 steps, long before convergence, and one uses a learning rate that **diverges**. So "close to the least-squares answer" isn't enough: you have to take the same steps as the reference, in the same order, with the same constants.

Three details decide that: the factor of 2 in the gradient, averaging over `n` rather than summing, and computing both gradients from the **same** residual before updating either parameter.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `X` | float array, shape `(n, d)`, `1 <= n <= 200`, `1 <= d <= 8` | the features |
| `y` | float array, shape `(n,)` | the targets |
| `lr` | float `> 0` | the step size $\eta$ |
| `n_iters` | int, `0 <= n_iters <= 2000` | exactly how many updates to make |
| return | tuple `(w, b)` | `w` shape `(d,)`, `b` a Python float |

Details that are easy to miss:

- **`n_iters = 0`** means return the starting point, `w = 0`, `b = 0`.
- **The loss is the mean**, $\frac{1}{n}\sum r_i^2$, so the gradient has $\frac{2}{n}$ in front.
- **Divergence is allowed.** "diverging lr" expects `w = [319043.2434]`. Don't clip, normalize or stop early.
- **Simultaneous update.** Both gradients come from the residual computed at the start of the iteration.

## 3. The math

The model is $\hat y = Xw + b\mathbf{1}$, and the loss is the mean squared error

$$
L(w, b) = \frac{1}{n}\sum_{i=1}^{n} r_i^2, \qquad r = Xw + b\mathbf{1} - y \in \mathbb{R}^n .
$$

**Deriving the gradients.** Differentiate one term with the chain rule. Since $r_i = \sum_k X_{ik} w_k + b - y_i$, we have $\partial r_i / \partial w_j = X_{ij}$ and $\partial r_i / \partial b = 1$. So

$$
\frac{\partial L}{\partial w_j} = \frac{1}{n}\sum_i 2 r_i \frac{\partial r_i}{\partial w_j} = \frac{2}{n}\sum_i X_{ij}\, r_i,
\qquad
\frac{\partial L}{\partial b} = \frac{2}{n}\sum_i r_i .
$$

The sum $\sum_i X_{ij} r_i$ over all $j$ is the vector $X^\top r$, so in matrix form

$$
\nabla_w L = \frac{2}{n} X^\top r \in \mathbb{R}^d, \qquad \frac{\partial L}{\partial b} = \frac{2}{n}\mathbf{1}^\top r \in \mathbb{R}.
$$

The 2 comes from differentiating the square. Losses written as $\frac{1}{2n}\sum r_i^2$ exist precisely to cancel it; this problem doesn't use that convention.

**The update.** Gradient descent moves against the gradient:

$$
w \leftarrow w - \eta\, \nabla_w L, \qquad b \leftarrow b - \eta\, \frac{\partial L}{\partial b}.
$$

**When it converges, and when it diverges.** Stack $\theta = [w; b]$ and $A = [X \;\; \mathbf{1}]$. The loss is a quadratic with constant Hessian $H = \frac{2}{n}A^\top A$, and the update is $\theta \leftarrow \theta - \eta H(\theta - \theta^\star)$, where $\theta^\star$ is the least-squares solution (problem 10). So the error $e = \theta - \theta^\star$ evolves as

$$
e_{t+1} = (I - \eta H)\, e_t .
$$

In the eigenbasis of $H$, each component is multiplied by $1 - \eta\lambda$ every step. It shrinks when $|1 - \eta\lambda| < 1$, that is, when $\eta < 2/\lambda$. Convergence requires $\eta < 2/\lambda_{\max}$, and the slowest component shrinks by $1 - \eta\lambda_{\min}$ per step.

For "diverging lr", $H$ has eigenvalues `0.2994` and `16.7006`, so the limit is $2/16.70 = 0.1198$. With $\eta = 0.2$ the large component is multiplied by $1 - 0.2 \cdot 16.70 = -2.34$ every step: it flips sign and grows by 2.34x. After 15 steps that's about $2.34^{15} \approx 3.5 \times 10^5$, which is why `w` ends at `319043`.

## 4. Trace an example by hand

**Example 1:** `X = [[1], [2], [3]]` (shape `(3, 1)`), `y = [2, 4, 6]`, `lr = 0.1`, `n_iters = 1`.

```python
w, b = np.zeros(1), 0.0                 # [0.], 0.0
r = X @ w + b - y                       # [-2, -4, -6]                (3,)
dw = (2 / 3) * (X.T @ r)                # X.T @ r = [1*-2 + 2*-4 + 3*-6] = [-28]  ->  [-18.6667]   (1,)
db = (2 / 3) * np.sum(r)                # (2/3) * -12 = -8.0
w = w - 0.1 * dw                        # [1.8667]
b = b - 0.1 * db                        # 0.8
```

That's the expected `([1.8667], 0.8)`. The residuals are all negative (predictions too low), so both gradients are negative and both parameters move up.

**"offset only"**: `X` is all zeros, `y = 7`, `lr = 0.25`. Now `dw` is always 0, and $\partial L/\partial b = 2(b - 7)$, so each step does $b \leftarrow b - 0.5(b - 7)$: the gap to 7 halves. After 10 steps $b = 7(1 - 0.5^{10}) = 6.99316$, exactly the expected value.

**Example 2** runs 200 steps with $\eta = 0.05$. The least-squares answer is `w = [2, 1]`, `b = 0.125`. GD reaches `w = [1.9925, 0.9988]`, `b = 0.1361`. The slowest eigen-direction shrinks by `0.9788` per step, so after 200 steps about 1.4% of the initial error remains. That's why the judge compares with the exact GD trajectory rather than with the closed form.

## 5. Key idea: one residual per iteration

Compute `r` once, derive **both** gradients from it, then update both parameters. If you update `w` first and then recompute `r` to update `b`, `b`'s gradient sees the new `w`. That's a different algorithm (block coordinate descent). It often converges to the same place, so a test that runs to convergence can't tell the difference: "three features converge" and "offset only" both pass with that bug. But it takes a different path, and on Example 1 it gives `b = 0.0533` instead of `0.8`, because the updated `w = 1.8667` already explains most of `y`.

## 6. Plan before you code

```
w = zeros(d), b = 0.0
repeat n_iters times:
    r = X @ w + b - y                  # (n,), from the current parameters
    dw = (2/n) X^T r                   # (d,)
    db = (2/n) sum(r)                  # scalar
    w = w - lr * dw
    b = b - lr * db                    # both from the same r
return w, float(b)
```

| variant | Example 1 result | effect |
|---|---|---|
| as specified | `w = [1.8667]`, `b = 0.8` | correct |
| no factor 2 | `w = [0.9333]` | half the step |
| sum instead of mean | `w = [5.6]` | step scales with `n`; diverges on most tests |
| recompute `r` before updating `b` | `b = 0.0533` | different trajectory |
| residual written as `y - ŷ` with the same `-` update | `w = [-1.8667]` | ascends the loss and diverges |

## 7. Build it one piece at a time

**Step 1: initialize.**

```python
n, d = X.shape
w = np.zeros(d)      # (d,)
b = 0.0
```

**Step 2: the residual and both gradients.**

```python
r = X @ w + b - y                  # (n, d) @ (d,) -> (n,); the scalar b broadcasts
dw = (2.0 / n) * (X.T @ r)         # (d, n) @ (n,) -> (d,)
db = (2.0 / n) * np.sum(r)         # scalar
```

`X.T @ r` is the vectorized form of $\sum_i X_{ij} r_i$ for every $j$. Writing `X * r` instead fails, because `(n, d) * (n,)` aligns `r` with the `d` axis. You'd need `r[:, None]`.

**Step 3: update both, then loop.**

```python
w = w - lr * dw                    # (d,)
b = b - lr * db
```

The only Python loop is over iterations. It can't be vectorized away, because each step depends on the previous one.

**Step 4: return.** `float(b)` turns the NumPy scalar from `np.sum` into a Python float.

## 8. Full solution

```python
# NumPy gives matrix-vector products and sums
import numpy as np


# full-batch gradient descent on MSE from w = 0, b = 0; returns (w (d,), b float)
def linear_regression_gd(X: np.ndarray, y: np.ndarray, lr: float, n_iters: int) -> tuple:
    # n samples, d features
    n, d = X.shape
    # start every weight at zero, as the problem specifies
    w = np.zeros(d)
    # bias also starts at zero
    b = 0.0
    # exactly n_iters updates; each one depends on the last, so this loop stays
    for _ in range(n_iters):
        # residual from the current parameters, (n,); positive where we predict too high
        r = X @ w + b - y
        # gradient of (1/n) sum r^2 w.r.t. w: the 2 is from the square, (d, n) @ (n,) -> (d,)
        dw = (2.0 / n) * (X.T @ r)
        # gradient w.r.t. b from the same residual, so both updates are simultaneous
        db = (2.0 / n) * np.sum(r)
        # step downhill for the weights
        w = w - lr * dw
        # and for the bias (r is not recomputed in between)
        b = b - lr * db
    # b is a NumPy scalar after the updates; the judge wants a Python float
    return w, float(b)
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `([1.8667], 0.8)` | one exact step: the 2, the `1/n`, both gradients |
| Example 2 | `([1.9925, 0.9988], 0.1361)` | 200 steps, not yet at the OLS answer `([2, 1], 0.125)` |
| zero iterations | `([0, 0], 0)` | the loop runs zero times |
| few steps | `([1.1036, -1.4618, 0.4275], 2.1454)` | an early trajectory, sensitive to every constant |
| three features converge | `([1.493, -1.9954, 0.5498], 4.001)` | near the true `[1.5, -2, 0.5]`, `4` |
| bigger problem | `b = -1.0041` | `d = 5`, 300 steps |
| offset only | `([0], 6.99316)` | only the bias learns: $7(1 - 0.5^{10})$ |
| diverging lr | `([319043.2434], 108513)` | $\eta$ above $2/\lambda_{\max}$; no clipping |

## 10. Complexity

- **Time:** $O(T\,nd)$ for $T$ = `n_iters` iterations: two matrix-vector products per step.
- **Memory:** $O(n + d)$ beyond the input, for `r`, `w` and `dw`.

Compare problem 10's closed form, $O(nd^2)$ once. For small $d$, the closed form wins. Gradient descent wins when $d$ is huge (no $d \times d$ system), when the data doesn't fit in memory (switch to minibatches, i.e. SGD), or when the model isn't linear and there is no closed form at all. The number of iterations needed scales with the condition number $\lambda_{\max}/\lambda_{\min}$ of $H$, which is why standardizing features (problem 7) speeds it up so much.

## 11. If you got Wrong Answer

- **Example 1 gives `w = [0.9333]`, half the expected value.** You dropped the factor 2 (`wrong_no_factor_two.py`). It fails every case with at least one step, though on "three features converge" the difference is tiny (`0.549761` vs `0.549756`), because both versions approach the same minimum.
- **Example 1's `w` is right but `b = 0.0533` instead of `0.8`.** You recomputed the residual after updating `w` (`wrong_sequential_update.py`). It passes "three features converge" and "offset only", where the two paths end at the same point.
- **Huge values or `nan` on most cases; Example 1 gives `w = [5.6]`.** You summed instead of averaging, so the step is `n` times too big.
- **Every sign is flipped and values explode.** You wrote the residual as `y - ŷ` but kept `w - lr * dw`. With that residual, the gradient is $-\frac{2}{n}X^\top r$.
- **"shape mismatch, expected (1,), got (3,)", or a broadcasting error.** You wrote `X * r` instead of `X.T @ r`.

## 12. Follow-ups an interviewer might ask

- *How do you pick the learning rate?* It must be below $2/\lambda_{\max}$ of $H = \frac{2}{n}A^\top A$ (section 3). In practice, try a few values on a log scale, or use a line search. Adaptive optimizers (problems 50–53) rescale per parameter.
- *What changes for stochastic gradient descent?* Use a random minibatch of rows each step. Each step is cheaper and noisier, and the learning rate usually decays (problem 54, cosine-schedule-with-warmup).
- *How does this compare to the closed form?* Same minimum (problem 10). From $w = 0$, GD converges to the minimum-norm solution even when the problem is rank-deficient, because its updates stay in the row space of $A$.
- *How do you add L2 regularization?* Add $\lambda\lVert w\rVert^2$ to the loss, which adds $2\lambda w$ to the gradient: "weight decay" (problem 12, ridge-regression; problem 53, adamw).
- *Why does momentum help here?* On a long, narrow valley (a large condition number) plain GD zig-zags across the steep direction. Momentum averages successive gradients, so the zig-zags cancel and the slow direction accumulates speed (problem 48, sgd-momentum).
