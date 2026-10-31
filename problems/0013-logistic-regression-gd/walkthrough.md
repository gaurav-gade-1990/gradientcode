## 1. What the problem is really asking

Logistic regression is the simplest classifier you can train with gradients: a linear score $z = x^\top w + b$, squashed into a probability by the sigmoid, and trained to minimize cross-entropy. It's also a one-neuron neural network, so everything here (the forward pass, the gradient with respect to the logits, the stable activation) carries straight over to deep learning.

Under the story, this is problem 11's gradient-descent loop with two changes:

1. **A different gradient.** The sigmoid and the cross-entropy cancel, so the gradient with respect to the logits is just $(p - y)/n$. You have to derive (or trust) that, and get the sign and the $1/n$ right.
2. **A numerically stable sigmoid.** Features reach the thousands, so logits reach $\pm 10^5$. The textbook formula $e^z / (1 + e^z)$ evaluates to `inf / inf = nan` there, and one `nan` poisons every weight.

The judge compares `(w, b)` after exactly `n_iters` steps with the reference (`rtol=1e-6`), so you must follow the same trajectory: same start, same gradient, simultaneous updates.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `X` | float array, shape `(n, d)`, `1 <= n <= 200`, `1 <= d <= 8` | features; may be in the thousands |
| `y` | float array, shape `(n,)`, each `0.0` or `1.0` | labels |
| `lr` | float `> 0` | step size $\eta$ |
| `n_iters` | int, `0 <= n_iters <= 2000` | exact number of updates |
| return | tuple `(w, b)` | `w` shape `(d,)`, `b` a Python float |

Details that are easy to miss:

- **No factor of 2.** Unlike problem 11's MSE, the cross-entropy gradient is $\frac{1}{n}X^\top(p - y)$.
- **The sign is $p - y$.** Predictions above the label push the weights down.
- **Labels can all be one class** ("all one class"). Then the data is perfectly separable by the bias alone, and `b` keeps growing; return whatever the updates produce.
- **`n_iters = 0`** returns zeros.

## 3. The math

The model and loss are

$$
z = Xw + b\mathbf{1} \in \mathbb{R}^n, \qquad p = \sigma(z), \qquad
L = -\frac{1}{n}\sum_{i=1}^{n}\Big[y_i \log p_i + (1 - y_i)\log(1 - p_i)\Big],
$$

with $\sigma(z) = 1/(1 + e^{-z})$ applied elementwise.

**Step 1: the derivative of the sigmoid.** Differentiate $\sigma(z) = (1 + e^{-z})^{-1}$:

$$
\sigma'(z) = \frac{e^{-z}}{(1 + e^{-z})^2} = \frac{1}{1 + e^{-z}}\cdot\frac{e^{-z}}{1 + e^{-z}} = \sigma(z)\,\big(1 - \sigma(z)\big).
$$

(The second factor is $1 - \sigma(z)$ because $\frac{e^{-z}}{1 + e^{-z}} = 1 - \frac{1}{1 + e^{-z}}$.)

**Step 2: the gradient with respect to one logit.** Only term $i$ of the sum depends on $z_i$. By the chain rule, with $\partial p_i/\partial z_i = p_i(1 - p_i)$:

$$
\frac{\partial L}{\partial z_i}
= -\frac{1}{n}\left[\frac{y_i}{p_i} - \frac{1 - y_i}{1 - p_i}\right] p_i(1 - p_i)
= -\frac{1}{n}\Big[y_i(1 - p_i) - (1 - y_i)p_i\Big]
= \frac{p_i - y_i}{n}.
$$

The $p_i(1 - p_i)$ from the sigmoid cancels the denominators from the logs. That cancellation is why cross-entropy is the natural loss for a sigmoid: the gradient never vanishes just because the sigmoid saturated, unless the prediction is also right.

**Step 3: the parameter gradients.** Since $z_i = x_i^\top w + b$, we have $\partial z_i/\partial w_j = X_{ij}$ and $\partial z_i/\partial b = 1$:

$$
\nabla_w L = \sum_i \frac{\partial L}{\partial z_i}\, x_i = \frac{1}{n}X^\top(p - y) \in \mathbb{R}^d,
\qquad
\frac{\partial L}{\partial b} = \frac{1}{n}\sum_i (p_i - y_i).
$$

Same shape as linear regression, with $p$ in place of $\hat y$ and no 2.

**Step 4: a stable sigmoid.** Two ways to write it, each safe on one side:

- $\frac{1}{1 + e^{-z}}$: for $z \ll 0$, $e^{-z}$ overflows to `inf`, but `1 / inf = 0.0`, which is the right limit. NumPy warns and the value is fine.
- $\frac{e^{z}}{1 + e^{z}}$: for $z \gg 0$, both numerator and denominator are `inf`, and `inf / inf = nan`. That's the dangerous form.

The robust approach only ever exponentiates a non-positive number. Let $e = e^{-|z|} \in (0, 1]$. Then

$$
\sigma(z) = \begin{cases} \dfrac{1}{1 + e} & z \ge 0 \\[2mm] \dfrac{e}{1 + e} & z < 0 \end{cases}
$$

Both branches are exact rewrites (multiply the top and bottom of $\frac{1}{1 + e^{-z}}$ by $e^{z}$ for the second), and neither can overflow or produce `nan`. For $z = -10^5$, $e$ underflows to `0.0` and $\sigma = 0$ exactly, which is the correct value to float64 precision.

## 4. Trace an example by hand

**Example 1:** `X = [[1], [2], [-1], [-2]]`, `y = [1, 1, 0, 0]`, `lr = 0.5`, one step.

```python
w, b = [0.], 0.0
z = X @ w + b                       # [0, 0, 0, 0]                 (4,)
p = sigmoid(z)                      # [0.5, 0.5, 0.5, 0.5]
g = p - y                           # [-0.5, -0.5, 0.5, 0.5]       (4,)
dw = X.T @ g / 4                    # (-0.5 - 1.0 - 0.5 - 1.0) / 4 = [-0.75]   (1,)
db = g.mean()                       # 0.0
w = w - 0.5 * dw                    # [0.375]
b = b - 0.5 * db                    # 0.0
```

At $w = 0$ every prediction is 0.5. The positive examples have positive $x$, so the gradient pushes $w$ up. The classes are balanced, so the bias gradient is 0.

**"huge logits":** `X = [[1000], [2000], [-1500], [-500]]`, `y = [1, 1, 0, 0]`, `lr = 0.1`, 20 steps. The first step is like Example 1 but scaled: `dw = [-625]`, so `w = [62.5]`. Now the logits are `[62500, 125000, -93750, -31250]`. The stable sigmoid gives `p = [1, 1, 0, 0]` exactly, so `g = 0` and nothing moves for the remaining 19 steps. The expected answer is `([62.5], 0)`.

With `np.exp(z) / (1 + np.exp(z))`, the logit `62500` gives `inf / inf = nan`, `dw` becomes `nan`, and every later value is `nan`.

**Example 2** has a symmetry worth noticing. Swapping the two feature columns maps the dataset onto itself with the same labels, so the gradients for $w_1$ and $w_2$ are always equal, and after 100 steps `w = [1.5533, 1.5533]`, `b = -2.5442`.

## 5. Key idea: `np.where` evaluates both branches

`np.where(z >= 0, 1 / (1 + e), e / (1 + e))` computes **both** arrays in full and then picks elementwise. That's why the stable version builds both branches from the same safe `e = exp(-|z|)`: whichever branch is discarded, it was still computed, and it must not overflow either. A version like `np.where(z >= 0, 1 / (1 + np.exp(-z)), np.exp(z) / (1 + np.exp(z)))` looks guarded but still evaluates `np.exp(z)` for large positive `z`, producing overflow warnings (and `nan` in the branch it throws away). Guarding with `where` only works when every branch is safe on every input.

## 6. Plan before you code

```
sigmoid(z): e = exp(-|z|); return 1/(1+e) where z >= 0, else e/(1+e)

w = zeros(d), b = 0
repeat n_iters times:
    p = sigmoid(X @ w + b)             # (n,)
    g = p - y                          # (n,), dL/dz times n
    dw = X^T g / n                     # (d,)
    db = mean(g)                       # scalar
    w = w - lr * dw;  b = b - lr * db  # simultaneous
return w, float(b)
```

| variant | Example 1 `w` | "huge logits" |
|---|---|---|
| reference | `0.375` | `62.5` |
| `exp(z) / (1 + exp(z))` | `0.375` | `nan` |
| `1 / (1 + exp(-z))` (no guard) | `0.375` | `62.5` with overflow warnings |
| summed gradient | `1.5` | `250` |
| `y - p` with the same update | `-0.375` | `-2437.5` |

## 7. Build it one piece at a time

**Step 1: the stable sigmoid.**

```python
def sigmoid(z):
    e = np.exp(-np.abs(z))                                   # (n,), every value in (0, 1]
    return np.where(z >= 0, 1.0 / (1.0 + e), e / (1.0 + e))  # (n,)
```

**Step 2: the forward pass and the logit gradient.**

```python
p = sigmoid(X @ w + b)      # (n, d) @ (d,) -> (n,); scalar b broadcasts
g = p - y                   # (n,)
```

**Step 3: parameter gradients and the update.**

```python
dw = X.T @ g / n            # (d, n) @ (n,) -> (d,)
db = np.mean(g)             # scalar, = sum(g) / n
w = w - lr * dw
b = b - lr * db
```

Both updates use the same `g`, computed before either parameter changed.

## 8. Full solution

```python
# NumPy gives exp, where and matrix-vector products
import numpy as np


# a sigmoid that never overflows, for logits as large as +-1e5
def sigmoid(z):
    # exponentiate only -|z| <= 0, so e is in (0, 1] and can't overflow
    e = np.exp(-np.abs(z))
    # z >= 0: 1 / (1 + e^-z); z < 0: e^z / (1 + e^z); both are built from the safe e,
    # which matters because np.where evaluates both branches everywhere
    return np.where(z >= 0, 1.0 / (1.0 + e), e / (1.0 + e))


# full-batch gradient descent on mean binary cross-entropy; returns (w (d,), b float)
def logistic_regression_gd(X: np.ndarray, y: np.ndarray, lr: float, n_iters: int) -> tuple:
    # n samples, d features
    n, d = X.shape
    # start from zero weights, as specified
    w = np.zeros(d)
    # and a zero bias
    b = 0.0
    # exactly n_iters updates
    for _ in range(n_iters):
        # predicted probability of class 1 for every sample, (n,)
        p = sigmoid(X @ w + b)
        # dL/dz times n: the sigmoid's slope cancels against the log's, leaving p - y
        g = p - y
        # weight gradient of the mean loss (no factor 2 here), (d, n) @ (n,) -> (d,)
        dw = X.T @ g / n
        # bias gradient from the same g, so the two updates are simultaneous
        db = np.mean(g)
        # step downhill: predictions above the label push weights down
        w = w - lr * dw
        # same step for the bias
        b = b - lr * db
    # return the bias as a Python float
    return w, float(b)
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `([0.375], 0)` | one exact step: $p - y$, the $1/n$, the sign |
| Example 2 | `([1.5533, 1.5533], -2.5442)` | 100 steps; symmetric data gives equal weights |
| zero iterations | `([0, 0, 0], 0)` | no steps |
| noisy 2d | `([2.8576, -1.6681], 0.611)` | the same signs and rough proportions as the generating `[2, -1]`, `0.5` |
| five features | `b = -0.3492` | general case |
| huge logits | `([62.5], 0)` | logits up to `125000`: the stable sigmoid, no `nan` |
| separable large scale | `([5.9348, -0.1339], -0.2692)` | logits in the hundreds and thousands, mixed signs |
| all one class | `([0.152, 0.2229], 3.12)` | the bias grows to push every $p$ toward 1 |

## 10. Complexity

- **Time:** $O(T\,nd)$ for $T$ iterations: two matrix-vector products and $O(n)$ elementwise work per step.
- **Memory:** $O(n + d)$ beyond the input.

Unlike linear regression, there's no closed form, so iteration isn't optional. On separable data ("huge logits", "all one class") the loss has no minimum: it keeps decreasing as $\lVert w\rVert \to \infty$, so plain gradient descent never stops growing the weights. In practice you add L2 regularization (which restores a unique minimum) or stop early. For larger problems, second-order methods like L-BFGS or Newton's method (IRLS) converge in far fewer iterations, because the Hessian $\frac{1}{n}X^\top \operatorname{diag}(p(1-p)) X$ is cheap to form when $d$ is small.

## 11. If you got Wrong Answer

- **`nan` on "huge logits" and "separable large scale" only.** Your sigmoid is `np.exp(z) / (1 + np.exp(z))` (`wrong_exp_ratio_sigmoid.py`). Every small-logit test passes, which is why it's easy to ship.
- **Every weight has the wrong sign; Example 1 gives `-0.375`.** You used `y - p` with `w - lr * dw` (`wrong_gradient_ascent.py`). That climbs the loss.
- **Example 1 gives `1.5` instead of `0.375`.** You summed instead of averaging (`wrong_sum_gradient.py`): the step is `n` times too big.
- **Example 1 gives `0.75`.** You added problem 11's factor of 2. Cross-entropy doesn't have one.
- **Example 1 passes but Example 2 gives `w[0] = 1.5756` instead of `1.5533`.** You recomputed `p` after updating `w` and used it for `b`. Example 1 hides it because its bias gradient is 0 at every step it takes. Compute `g` once per iteration.

## 12. Follow-ups an interviewer might ask

- *How do you compute the loss itself stably?* Never take `np.log(p)` of a saturated sigmoid; `p = 1.0` makes `log(1 - p) = -inf`. Use the logit form $\ell = \max(z, 0) - yz + \log(1 + e^{-|z|})$ (problem 29, binary-log-loss).
- *What's the multiclass version?* Softmax regression: $p = \operatorname{softmax}(XW + b)$ and the logit gradient is again $(P - Y)/n$ with one-hot $Y$ (problems 1, 5 and 36).
- *What happens on perfectly separable data?* The weights grow without bound and the loss tends to 0 ("huge logits" freezes only because the sigmoid saturates exactly). Add L2 regularization or stop early.
- *Why cross-entropy and not MSE?* With MSE the gradient picks up a $p(1-p)$ factor that goes to 0 when the sigmoid saturates, even on wrong predictions, so learning stalls. Cross-entropy cancels it (section 3).
- *How do you turn probabilities into decisions?* Threshold at 0.5 by default, but pick the threshold from the costs of each error type, using precision/recall or ROC curves (problems 26 and 27).
