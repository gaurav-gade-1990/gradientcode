## 1. What the problem is really asking

The perceptron (Rosenblatt, 1958) is the original learning machine: a linear classifier $\operatorname{sign}(w^\top x + b)$ that learns by fixing its mistakes one at a time. It looks at each sample in turn, and if the sample is on the wrong side of the line (or exactly on it), it moves the line toward that sample.

Under the story, this is an **online algorithm**: a sequential loop where each decision depends on the updates made just before it. That's the whole difficulty. You can't vectorize the inner loop, and you can't batch the updates, because the second sample must be judged by the weights after the first sample's update. The judge compares `(w, b)` with the reference to `rtol=1e-9`, so the visiting order, the `<= 0` test and the update rule all have to match exactly.

It's also a stepping stone: problem 15 (linear-svm-hinge-sgd) is the same loop with a margin and a regularizer.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `X` | float array, shape `(n, d)`, `1 <= n <= 100`, `1 <= d <= 6` | samples, visited in row order |
| `y` | float array, shape `(n,)`, each `-1.0` or `+1.0` | labels; the sign convention matters |
| `n_epochs` | int, `0 <= n_epochs <= 50` | full passes over the data, all of them |
| `lr` | float `> 0`, default `1.0` | step size $\eta$ |
| return | tuple `(w, b)` | `w` shape `(d,)`, `b` a Python float |

Details that are easy to miss:

- **A score of exactly zero is a mistake.** At the start $w = 0$, $b = 0$, so every score is 0. With a strict `< 0` test the model never updates at all.
- **Labels are $\pm 1$, not $\{0, 1\}$.** The update $w \mathrel{+}= \eta y_i x_i$ uses the label's sign to pick the direction.
- **Run every epoch.** Don't stop when an epoch makes no mistakes; the problem asks for all `n_epochs`, though on separable data the later ones change nothing.
- **Order is part of the input** ("order matters"). Visiting the same samples in reverse order gives a different answer.

## 3. The math

**The mistake condition.** The model predicts $\hat y = \operatorname{sign}(w^\top x + b)$. The quantity $m_i = y_i(w^\top x_i + b)$ is positive exactly when the prediction has the right sign. So $m_i \le 0$ means "wrong or undecided".

**The update, and why it helps.** On a mistake, $w \leftarrow w + \eta y_i x_i$ and $b \leftarrow b + \eta y_i$. The new score on the same sample is

$$
y_i\big((w + \eta y_i x_i)^\top x_i + (b + \eta y_i)\big)
= m_i + \eta\, y_i^2\big(\lVert x_i\rVert^2 + 1\big)
= m_i + \eta\big(\lVert x_i\rVert^2 + 1\big),
$$

using $y_i^2 = 1$. Every update raises that sample's score by a strictly positive amount. It doesn't guarantee the sample is fixed in one step, and it can break other samples, which is why the algorithm loops.

**The perceptron as gradient descent.** The perceptron loss for one sample is $\ell_i(w, b) = \max(0, -y_i(w^\top x_i + b))$. Where $m_i < 0$, its gradient is

$$
\nabla_w \ell_i = -y_i x_i, \qquad \frac{\partial \ell_i}{\partial b} = -y_i ,
$$

and where $m_i > 0$ it is 0. So the update is exactly a stochastic gradient step $w \leftarrow w - \eta\nabla_w \ell_i$ on one sample at a time. At $m_i = 0$ the loss has a kink; the perceptron chooses the subgradient $-y_i x_i$ there, which is what makes it able to start from $w = 0$. Problem 15's hinge loss $\max(0, 1 - m_i)$ shifts the kink to $m_i = 1$, demanding a margin.

**Convergence on separable data (Novikoff).** Suppose some unit vector $u$ (folding $b$ into $w$ with an extra constant feature) separates the data with margin $\gamma$: $y_i u^\top x_i \ge \gamma > 0$, and let $R = \max_i \lVert x_i\rVert$. Starting from 0 with $\eta = 1$, after $k$ mistakes:

- each mistake adds at least $\gamma$ to $u^\top w$, so $u^\top w \ge k\gamma$;
- each mistake adds at most $R^2$ to $\lVert w\rVert^2$ (because $\lVert w + y x\rVert^2 = \lVert w\rVert^2 + 2y\,w^\top x + \lVert x\rVert^2$, and $y\,w^\top x \le 0$ on a mistake), so $\lVert w\rVert^2 \le kR^2$.

Cauchy–Schwarz gives $k\gamma \le u^\top w \le \lVert w\rVert \le \sqrt{k}R$, so $k \le (R/\gamma)^2$. The number of mistakes is finite, whatever the order. On "separable many epochs", all mistakes happen in the first epoch (2 of them), and the next 29 epochs change nothing.

**Non-separable data.** No such $u$ exists, the bound fails, and the weights keep moving forever. XOR is the classic example.

## 4. Trace an example by hand

**Example 1:** `X = [[2, 1], [-1, -1], [1, 2]]`, `y = [1, -1, 1]`, one epoch, `lr = 1`.

| i | score $y_i(w^\top x_i + b)$ | mistake? | w after | b after |
|---|---|---|---|---|
| 0 | `1 * (0 + 0) = 0` | yes (`<= 0`) | `[2, 1]` | `1` |
| 1 | `-1 * (-2 - 1 + 1) = 2` | no | `[2, 1]` | `1` |
| 2 | `1 * (2 + 2 + 1) = 5` | no | `[2, 1]` | `1` |

Result `([2, 1], 1)`. The very first update only happens because zero counts as a mistake.

**"xor never converges":** `X = [[0, 0], [0, 1], [1, 0], [1, 1]]`, `y = [-1, 1, 1, -1]`, 7 epochs.

| i | score | w after | b after |
|---|---|---|---|
| 0 | `0` (mistake) | `[0, 0]` | `-1` |
| 1 | `1 * (0 + -1) = -1` (mistake) | `[0, 1]` | `0` |
| 2 | `1 * (0 + 0) = 0` (mistake) | `[1, 1]` | `1` |
| 3 | `-1 * (1 + 1 + 1) = -3` (mistake) | `[0, 0]` | `0` |

Every sample is a mistake, and the four updates sum to zero: $-[0,0] + [0,1] + [1,0] - [1,1] = 0$ and $-1 + 1 + 1 - 1 = 0$. Each epoch ends exactly where it started, so after 7 epochs the answer is `([0, 0], 0)`. That's a cycle, not convergence.

**"order matters":** five samples, 5 epochs. In the given order, epoch 0 makes three mistakes (at samples 0, 1 and 2) and lands at `w = [2, 0]`, `b = -1`, which separates everything; epochs 1–4 change nothing. Visiting the same samples in reverse order lands at `w = [3, -1]`, `b = -1` instead. Both separate the data; they're just different separators.

## 5. Key idea: online updates can't be batched

It's tempting to vectorize: find every misclassified sample with one comparison, sum their updates, apply once per epoch. That's a different algorithm (batch perceptron), and it gives different weights. On Example 1, all three samples score 0 at the start, so a batch step adds all three: `w = [2, 1] - [-1, -1] + [1, 2] = [4, 4]`, and the judge reports `w[0] = 4` instead of `2`. In the online version, the first update already fixes samples 1 and 2.

So the inner Python loop is required. With `n <= 100` and `n_epochs <= 50` that's at most 5000 iterations, which is fast.

## 6. Plan before you code

```
w = zeros(d), b = 0
for each epoch:
    for i = 0 .. n-1, in order:
        if y[i] * (X[i] . w + b) <= 0:        # zero is a mistake
            w = w + lr * y[i] * X[i]
            b = b + lr * y[i]
return w, float(b)
```

| variant | Example 1 | why |
|---|---|---|
| reference | `([2, 1], 1)` | correct |
| `< 0` instead of `<= 0` | `([0, 0], 0)` | never fires from `w = 0` |
| batch update per epoch | `w[0] = 4` | all three zero-score samples update at once |
| labels treated as `{0, 1}` | wrong signs | `y = 0` never moves the weights |

## 7. Build it one piece at a time

**Step 1: initialize.**

```python
n, d = X.shape
w = np.zeros(d)     # (d,)
b = 0.0
```

**Step 2: the epoch and sample loops.**

```python
for _ in range(n_epochs):
    for i in range(n):
        ...
```

**Step 3: the mistake test and the update.**

```python
if y[i] * (X[i] @ w + b) <= 0:    # X[i]: (d,), X[i] @ w: scalar
    w = w + lr * y[i] * X[i]      # (d,)
    b = b + lr * y[i]
```

`w = w + ...` creates a new array each time. `w += ...` would also work here, since `w` is our own array, but the explicit form avoids surprises if `w` ever aliases an input.

## 8. Full solution

```python
# NumPy gives zero vectors and dot products
import numpy as np


# online Rosenblatt perceptron from w = 0, b = 0; returns (w (d,), b float)
def perceptron(X: np.ndarray, y: np.ndarray, n_epochs: int, lr: float = 1.0) -> tuple:
    # n samples, d features
    n, d = X.shape
    # all weights start at zero, so every first score is exactly 0
    w = np.zeros(d)
    # the bias starts at zero too
    b = 0.0
    # run every epoch; no early stop, even when an epoch makes no mistakes
    for _ in range(n_epochs):
        # visit samples in the given order: each decision sees the updates just made
        for i in range(n):
            # wrong side of the line, or exactly on it (score 0 counts as a mistake)
            if y[i] * (X[i] @ w + b) <= 0:
                # move the hyperplane toward the sample: label +-1 picks the direction
                w = w + lr * y[i] * X[i]
                # the bias moves the same way, as if x had a constant 1 feature
                b = b + lr * y[i]
    # return the bias as a Python float
    return w, float(b)
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `([2, 1], 1)` | the `<= 0` test fires on the first sample; the rest are then correct |
| Example 2 | `([1], 0.5)` | `lr = 0.5`, 3 epochs on non-separable 1-D data |
| zero epochs | `([0, 0], 0)` | no passes |
| single sample | `([-0.5, 0.5, -2], -1)` | one update in epoch 0, then three quiet epochs |
| separable many epochs | `([0.6624, -1.4913], 0)` | two mistakes, all in epoch 0, then stable |
| noisy data | `([0.1477, 0.1807, -0.2272], 0)` | non-separable: 6 to 10 mistakes every epoch |
| order matters | `([2, 0], -1)` | sequential order; reversed order gives `([3, -1], -1)` |
| xor never converges | `([0, 0], 0)` | the four updates cancel every epoch |

## 10. Complexity

- **Time:** $O(E\,nd)$ for $E$ epochs: one dot product per sample per epoch.
- **Memory:** $O(d)$ for the weights.

The perceptron is cheap and streams naturally: it never needs more than one sample in memory. Its weaknesses are statistical. On separable data it stops at the **first** separator it finds, which may barely clear some points; on non-separable data it never settles, so the final weights depend on where you stop. The fixes are the averaged perceptron (return the average of $w$ over all steps, which is much more stable), the voted perceptron, or a margin plus regularization, which is the linear SVM of problem 15.

## 11. If you got Wrong Answer

- **`w` stays at zeros on every case.** You tested `< 0` instead of `<= 0` (`wrong_strict_mistake.py`). From $w = 0$ every score is 0, so nothing ever fires. It passes only "zero epochs" and "xor never converges", whose answers are zeros anyway.
- **Weights are too large; Example 1 gives `w[0] = 4`, "separable many epochs" gives `20.45`.** You batched the updates per epoch (`wrong_batch_update.py`). It also passes "single sample", where batch and online are the same thing.
- **Close to the answer on separable data but different elsewhere.** You shuffled the samples or visited them in another order. The order is fixed by the problem.
- **Weights never move with some labels.** Your labels were `{0, 1}`; a 0 label contributes nothing. They must be $\pm 1$.
- **Your loop stopped after a clean epoch.** That gives the same answer on separable data but not on "noisy data", where there's never a clean epoch; still, the problem asks for all `n_epochs`.

## 12. Follow-ups an interviewer might ask

- *Why doesn't it converge on XOR?* No line separates XOR, so Novikoff's bound doesn't apply and the updates cycle (section 4). A hidden layer fixes it: problem 47 (train-mlp-on-xor).
- *How many mistakes on separable data?* At most $(R/\gamma)^2$, independent of $n$ and of the order (section 3).
- *How do you make it more robust?* The averaged perceptron returns $\bar w = \frac{1}{T}\sum_t w_t$. It behaves like a large-margin classifier and is far less sensitive to the last few updates.
- *How does it relate to the SVM and logistic regression?* All three are linear models trained by (sub)gradient steps on a loss of the margin $m = y(w^\top x + b)$: perceptron $\max(0, -m)$, hinge $\max(0, 1 - m)$ (problem 15), logistic $\log(1 + e^{-m})$ (problem 13).
- *Can you kernelize it?* Yes. Since $w$ is always a sum of $\eta y_i x_i$ terms, store per-sample mistake counts and predict with $\sum_i \alpha_i y_i K(x_i, x)$. That handles XOR with a polynomial kernel.
