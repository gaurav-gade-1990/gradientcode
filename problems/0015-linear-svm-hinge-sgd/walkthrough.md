## 1. What the problem is really asking

A linear SVM is a linear classifier that doesn't just separate the classes; it tries to separate them **with room to spare**. Its loss, the hinge $\max(0, 1 - m)$, keeps penalizing a sample until its margin $m = y(w^\top x + b)$ reaches 1, and an L2 penalty on $w$ keeps the weights from growing to fake a large margin. Problem 14's perceptron stops at the first separator it finds; the SVM looks for the widest one.

Under the story, this is **subgradient descent on a non-smooth convex objective, with a decaying step size**. Three things make it different from problems 11 and 13:

1. The hinge has a kink, so you use a **subgradient**, defined by an active set of samples with margin strictly below 1.
2. The regularizer covers $w$ but **not** $b$.
3. The step size follows the **Pegasos schedule** $\eta_t = 1/(\lambda t)$, counting $t$ from 1.

The judge compares `(w, b)` after exactly `n_iters` steps with the reference (`rtol=1e-6`), so each of those details, plus averaging over all $n$ samples rather than just the active ones, changes the trajectory and fails.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `X` | float array, shape `(n, d)`, `1 <= n <= 200`, `1 <= d <= 8` | samples |
| `y` | float array, shape `(n,)`, each `-1.0` or `+1.0` | labels |
| `lam` | float `> 0` | regularization strength $\lambda$, also sets the step size |
| `n_iters` | int, `0 <= n_iters <= 1000` | exact number of full-batch steps |
| return | tuple `(w, b)` | `w` shape `(d,)`, `b` a Python float |

Details that are easy to miss:

- **Active means $m_i < 1$, strictly**, computed with the parameters at the start of the step.
- **Divide the hinge sum by $n$**, the total number of samples, not by the number of active ones.
- **No $\lambda b$ term.** The bias gradient is only the hinge part.
- **$t$ starts at 1.** The first step uses $\eta_1 = 1/\lambda$, which is large; that's intended.

## 3. The math

The objective is

$$
f(w, b) = \frac{\lambda}{2}\lVert w\rVert^2 + \frac{1}{n}\sum_{i=1}^{n}\max\big(0,\ 1 - m_i\big), \qquad m_i = y_i(w^\top x_i + b).
$$

**The subgradient of one hinge term.** As a function of $m$, $h(m) = \max(0, 1 - m)$ is $1 - m$ for $m < 1$ (slope $-1$) and $0$ for $m > 1$ (slope 0). At $m = 1$ any slope in $[-1, 0]$ is a valid subgradient; the problem picks 0 there, which is why the active test is strict. Since $\partial m_i / \partial w = y_i x_i$ and $\partial m_i / \partial b = y_i$, the chain rule gives, for $m_i < 1$,

$$
\nabla_w h(m_i) = -y_i x_i, \qquad \frac{\partial h(m_i)}{\partial b} = -y_i ,
$$

and zero otherwise. The regularizer contributes $\nabla_w \frac{\lambda}{2}\lVert w\rVert^2 = \lambda w$ and nothing for $b$. With the active set $\mathcal{A} = \{i : m_i < 1\}$:

$$
g_w = \lambda w - \frac{1}{n}\sum_{i \in \mathcal{A}} y_i x_i, \qquad g_b = -\frac{1}{n}\sum_{i \in \mathcal{A}} y_i .
$$

Compare the perceptron (problem 14): same direction $y_i x_i$, but its "active" condition was $m_i \le 0$. The SVM keeps pushing until the margin is 1.

**Vectorizing the active sum.** Let $a_i = y_i\,[m_i < 1]$, i.e. `ya = y * active`. Then $\sum_{i \in \mathcal{A}} y_i x_i = a^\top X$, a `(n,) @ (n, d) -> (d,)` product, and $\sum_{i \in \mathcal{A}} y_i = \sum_i a_i$.

**Why $\eta_t = 1/(\lambda t)$.** The objective is $\lambda$-strongly convex in $w$, and for strongly convex functions this schedule gives an $O(1/t)$ convergence rate (Shalev-Shwartz et al., "Pegasos"). It also has a neat closed form. Substitute $\eta_t$ into the $w$ update:

$$
w_{t+1} = w_t - \frac{1}{\lambda t}\big(\lambda w_t - h_t\big) = \Big(1 - \frac{1}{t}\Big) w_t + \frac{h_t}{\lambda t},
\qquad h_t = \frac{1}{n}\sum_{i \in \mathcal{A}_t} y_i x_i .
$$

Multiply by $t$: $t\,w_{t+1} = (t - 1)\,w_t + h_t/\lambda$. Summing from $t = 1$ (where $(t-1)w_t = 0$) to $T$ telescopes to

$$
w_{T+1} = \frac{1}{\lambda}\cdot\frac{1}{T}\sum_{t=1}^{T} h_t .
$$

After $T$ steps, $w$ is exactly $1/\lambda$ times the **average** hinge direction over all steps. On Example 2 that average gives `[1.46, 0.98]`, the expected answer. In particular, the first step, with $\eta_1 = 1/\lambda$, throws away the starting $w$ entirely ($1 - 1/1 = 0$). The bias has no $\lambda b$ term, so it doesn't telescope this way; it simply accumulates $-\eta_t g_b$.

## 4. Trace an example by hand

**Example 1:** `X = [[2], [1], [-1], [-3]]`, `y = [1, 1, -1, -1]`, `lam = 0.5`, one step.

```python
margins = y * (X @ w + b)      # [0, 0, 0, 0]: all < 1, so every sample is active   (4,)
ya = y * active                # [1, 1, -1, -1]                                      (4,)
ya @ X                         # 2 + 1 + 1 + 3 = [7]                                 (1,)
g_w = 0.5 * [0] - [7] / 4      # [-1.75]
g_b = -(1 + 1 - 1 - 1) / 4     # 0.0
eta = 1 / (0.5 * 1)            # 2.0
w = [0] - 2 * [-1.75]          # [3.5]
b = 0 - 2 * 0                  # 0.0
```

**Example 2:** five 2-D samples, `lam = 0.1`, 50 steps. The first few steps show how the active set and the big early steps behave:

| t | $\eta_t$ | margins at start of step | active | w after | b after |
|---|---|---|---|---|---|
| 1 | 10 | `[0, 0, 0, 0, 0]` | all 5 | `[7, 11]` | `-2` |
| 2 | 5 | `[27, 17.5, 25.5, 24, -7]` | sample 4 only | `[3, 5]` | `-3` |
| 3 | 3.33 | `[10, 5.5, 13.5, 13, -1]` | sample 4 only | `[1.667, 3]` | `-3.667` |
| 4 | 2.5 | `[4, 1.167, 9.833, 9.667, 1.333]` | none | `[1.25, 2.25]` | `-3.667` |

Step 1 overshoots wildly, because $\eta_1 = 1/\lambda = 10$. Then the $(1 - 1/t)$ shrinkage pulls $w$ back, and the active set flickers as margins cross 1. When nothing is active (step 4), the only force is the regularizer, which shrinks $w$ by $(1 - 1/4)$. At step 50 the active set is samples 0 and 1, whose margins (`0.9691`, `0.9896`) sit just under 1: they're the support vectors. The final answer is `w = [1.46, 0.98]`, `b = -2.1141`.

## 5. Key idea: average over $n$, not over the active set

The hinge term is $\frac{1}{n}\sum_{i=1}^{n}$, a mean over **all** samples, where inactive ones contribute 0. Dividing the active sum by $|\mathcal{A}|$ instead looks like "the average active direction", but it changes the objective: when only one sample is active, its pull becomes $n$ times stronger. On Example 1 every sample is active, so $|\mathcal{A}| = n$ and both versions agree, which is why that mistake passes the first visible test. On Example 2, where the active set shrinks to one sample by step 2, it gives `w[0] = 2.24` instead of `1.46`.

## 6. Plan before you code

```
w = zeros(d), b = 0
for t = 1 .. n_iters:
    margins = y * (X @ w + b)                 # (n,)
    ya = y where margins < 1, else 0          # (n,)
    g_w = lam * w - (ya @ X) / n              # (d,)
    g_b = -sum(ya) / n                        # no lam * b
    eta = 1 / (lam * t)
    w = w - eta * g_w;  b = b - eta * g_b
return w, float(b)
```

| variant | Example 1 | Example 2 `w[0]` |
|---|---|---|
| reference | `w = 3.5` | `1.46` |
| divide by the active count | `3.5` (all active) | `2.24` |
| regularize `b` too | `3.5` (`b` is 0 here) | `0.8` |
| schedule $1/(\lambda(t+1))$ | `1.75` | `1.451` |
| constant $\eta = 1/\lambda$ | `3.5` | `-1` |
| no $\lambda w$ term | `3.5` | `4.309` |

## 7. Build it one piece at a time

**Step 1: margins and the active set.**

```python
margins = y * (X @ w + b)    # (n, d) @ (d,) -> (n,), then elementwise with y
active = margins < 1         # (n,) booleans, strict
ya = y * active              # (n,): y_i where active, 0 elsewhere (True/False act as 1/0)
```

**Step 2: the subgradients.**

```python
g_w = lam * w - (ya @ X) / n     # (d,) - ((n,) @ (n, d) -> (d,)) / n
g_b = -np.sum(ya) / n            # scalar; the bias is not regularized
```

`ya @ X` is the vectorized $\sum_{i \in \mathcal{A}} y_i x_i$. Dividing by `n`, not by `active.sum()`, matches the objective.

**Step 3: the Pegasos step.**

```python
eta = 1.0 / (lam * t)            # t runs from 1, so no division by zero
w = w - eta * g_w
b = b - eta * g_b
```

Loop with `for t in range(1, n_iters + 1)`. Starting at 0 divides by zero; "fixing" that with `t + 1` shifts the whole schedule.

## 8. Full solution

```python
# NumPy gives vectorized margins, boolean masks and matrix-vector products
import numpy as np


# full-batch Pegasos subgradient descent on the soft-margin SVM; returns (w (d,), b float)
def linear_svm(X: np.ndarray, y: np.ndarray, lam: float, n_iters: int) -> tuple:
    # n samples, d features
    n, d = X.shape
    # start from zero weights, as specified
    w = np.zeros(d)
    # and a zero bias
    b = 0.0
    # t counts from 1 so the step size 1 / (lam * t) is defined on the first step
    for t in range(1, n_iters + 1):
        # signed margin of every sample under the current parameters, (n,)
        margins = y * (X @ w + b)
        # hinge is active (slope -1) only strictly inside the margin
        active = margins < 1
        # y_i for active samples, 0 for the rest, so one product sums only the active ones
        ya = y * active
        # L2 term on w plus the hinge part averaged over all n samples (not just active)
        g_w = lam * w - (ya @ X) / n
        # the bias gets only the hinge part: it is not regularized
        g_b = -np.sum(ya) / n
        # Pegasos schedule for a lam-strongly convex objective
        eta = 1.0 / (lam * t)
        # step the weights against the subgradient
        w = w - eta * g_w
        # and the bias, using the same margins (simultaneous update)
        b = b - eta * g_b
    # return the bias as a Python float
    return w, float(b)
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `([3.5], 0)` | one step: all active, $\eta_1 = 1/\lambda$ |
| Example 2 | `([1.46, 0.98], -2.1141)` | 50 steps with a changing active set |
| zero iterations | `([0, 0], 0)` | no steps |
| few steps | `([0.6954, -0.6866, 0.294, 0.2821], 1.1667)` | an early trajectory: schedule and averaging |
| separable | `([1.4057, 1.383], -1.0609)` | `w` points close to the generating direction `[1, 1]` |
| noisy with offset | `b = 1.4961` | the unregularized bias can grow to fit the `+0.8` offset |
| imbalanced labels | `b = 1.0371` | 16 vs 4 labels: penalizing `b` would distort it |
| strong regularization | `([0.0944, 0.1426], -0.2054)` | large $\lambda$ keeps `w` small; `b` is free |

## 10. Complexity

- **Time:** $O(T\,nd)$ for $T$ iterations: two matrix-vector products per step.
- **Memory:** $O(n + d)$ beyond the input.

Pegasos was designed for the **stochastic** setting: each step uses one sample (or a small batch), so the cost per step is $O(d)$, independent of $n$, and the number of steps for a given accuracy depends on $\lambda$, not on the dataset size. That's why it scales to millions of samples. Full-batch, as here, is easier to grade exactly. Linear SVMs at scale (liblinear) use dual coordinate descent instead, which converges faster for moderate $n$.

## 11. If you got Wrong Answer

- **Example 1 gives `w = 1.75` instead of `3.5`; everything else is slightly off.** Your step size is $1/(\lambda(t + 1))$ (`wrong_step_from_zero.py`): you started the counter at 0 and shifted to avoid dividing by zero.
- **Example 1 passes, Example 2 gives `w[0] = 2.24`.** You divided the hinge sum by the number of active samples (`wrong_mean_over_active.py`). It also passes "strong regularization", where every sample stays active.
- **Example 1 passes, "strong regularization" has `b = -0.048` instead of `-0.2054`.** You added `lam * b` to the bias gradient (`wrong_regularize_bias.py`). Its effect grows with $\lambda$.
- **Weights grow much too large; Example 2 gives `w[0] = 4.31`.** You dropped the `lam * w` term from `g_w`.
- **Weights oscillate or change sign; Example 2 gives `w[0] = -1`.** You used a constant $\eta = 1/\lambda$. Every step then resets $w$ to $h_t/\lambda$ instead of averaging.

## 12. Follow-ups an interviewer might ask

- *What are the support vectors here?* The samples with margin at or below 1 at the solution, the ones that keep appearing in the active set. In Example 2's last step they are samples 0 and 1. Only they determine $w$.
- *How does the SVM relate to the perceptron and logistic regression?* All three take (sub)gradient steps on a loss of the margin: perceptron $\max(0, -m)$ (problem 14), hinge $\max(0, 1 - m)$, logistic $\log(1 + e^{-m})$ (problem 13). Hinge is the only one that is exactly zero beyond a margin, which makes the solution sparse in samples.
- *How do you choose $\lambda$?* Cross-validate on a log scale (problem 31). Small $\lambda$ fits the training data tightly (narrow margin); large $\lambda$ prefers a wide margin and tolerates more violations. $\lambda$ plays the role of $1/(nC)$ in the usual $C$ parameterization.
- *Why not regularize the bias?* Penalizing $b$ pulls the boundary toward the origin, so the model's answer would depend on where the coordinate system is centered. It hurts most with imbalanced classes ("imbalanced labels").
- *How do you get non-linear boundaries?* Kernelize: in the dual the data appears only through inner products $x_i^\top x_j$, which you replace with a kernel $K(x_i, x_j)$. Or map features explicitly (random Fourier features) and keep this linear solver.
