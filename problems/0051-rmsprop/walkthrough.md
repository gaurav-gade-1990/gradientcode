## 1. What the problem is really asking

Adagrad (problem 50) divides each parameter's step by the root of its **total** squared gradient. That total never shrinks, so the step size only goes down, and long runs stall. RMSProp makes one change: replace the running sum with an **exponential moving average**. Old squared gradients fade, so the denominator tracks the *recent* gradient scale and the step can grow back after a burst of large gradients.

Strip the story and this is three elementwise lines again: decay the gradient, blend its square into the average, divide. What you have to get exactly right is which weight goes where (`alpha` multiplies the **old** average), where `eps` goes (outside the root), and what is *not* there (no bias correction; that's Adam). The judge compares `new_param` and `new_square_avg`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `param` | any, e.g. `(2,)`, `(4, 4)` | $\theta_{t-1}$ | decayed, then stepped |
| `grad` | same as `param` | the raw gradient | |
| `square_avg` | same as `param`, `>= 0` | $s_{t-1}$, the EMA of $g^2$; zeros at first | blended with this step's $g^2$ |
| `lr` | scalar, default `0.01` | $\eta$ | |
| `alpha` | scalar in `(0, 1)`, default `0.99` | the weight on the **old** average | |
| `eps` | scalar, default `1e-8` | added after the square root | |
| `weight_decay` | scalar, default `0.0` | $\lambda$, L2 added to the gradient | |

Easy to miss:

- **`alpha` is the "keep" weight.** `alpha = 0.99` keeps 99% of the old average and mixes in 1% of the new $g^2$. It is not a learning rate for the average.
- **`eps` defaults to `1e-8`** here, while Adagrad's is `1e-10`.
- **No bias correction**, unlike Adam. The first steps are large on purpose (section 3).

## 3. The math

The update:

$$
g = \nabla_\theta + \lambda\,\theta_{t-1}, \qquad
s_t = \alpha\, s_{t-1} + (1 - \alpha)\, g \odot g, \qquad
\theta_t = \theta_{t-1} - \eta\,\frac{g}{\sqrt{s_t} + \epsilon}.
$$

**What the average holds.** Unroll from $s_0 = 0$:

$$
s_t = (1-\alpha)\sum_{k=0}^{t-1} \alpha^k\, g_{t-k}^2 .
$$

The weights $(1-\alpha)\alpha^k$ sum to $1 - \alpha^t$, which approaches 1. So $s_t$ is a weighted average of recent squared gradients, with a memory of roughly $\frac{1}{1-\alpha}$ steps: about 100 steps at $\alpha = 0.99$. Compare Adagrad's $s_t = \sum_k g_k^2$, where nothing ever fades.

**The first step is large.** From $s_0 = 0$, $s_1 = (1-\alpha) g^2$, so $\sqrt{s_1} = \sqrt{1-\alpha}\,|g|$ and

$$
|\theta_1 - \theta_0| \approx \frac{\eta}{\sqrt{1-\alpha}} .
$$

At $\alpha = 0.99$ that's $10\eta$. The reason is that the weights $(1-\alpha)\alpha^k$ only sum to $1 - \alpha^t$, so early on $s_t$ underestimates the true mean square. Adam divides by $1 - \beta_2^t$ to correct for this; PyTorch's RMSprop does not, and you must not either.

**Recovery after a burst.** Feed both optimizers a gradient of `10` for 10 steps, then `1` from then on. The step `g / sqrt(s)` (in units of `lr`):

| step | gradient | Adagrad | RMSProp ($\alpha = 0.99$) |
|---|---|---|---|
| 1 | 10 | `1.0` | `10.0` |
| 10 | 10 | `0.3162` | `3.2339` |
| 11 | 1 | `0.0316` | `0.3249` |
| 60 | 1 | `0.0309` | `0.4023` |
| 210 | 1 | `0.0289` | `0.6825` |

Adagrad's denominator remembers the burst forever, so once the gradient drops to 1 its step stays near `0.03` and keeps falling. RMSProp's average forgets the burst, and its step climbs back.

## 4. Trace the examples by hand

**Example 1**: `param = [1, -1]`, `grad = [2, -2]`, `square_avg = [0, 0]`, `lr = 0.1`, `alpha = 0.75`. All `(2,)`.

| quantity | el. 0 | el. 1 |
|---|---|---|
| `g * g` | `4` | `4` |
| `new_avg = 0.75 * 0 + 0.25 * 4` | `1` | `1` |
| `sqrt(new_avg) + eps` | `1` (plus `1e-8`) | `1` |
| step `= 0.1 * g / 1` | `0.2` | `-0.2` |
| `new_param` | `0.8` | `-0.8` |

The move is `0.2`, which is $\eta / \sqrt{1 - \alpha} = 0.1 / 0.5$: the large first step from section 3.

**Example 2**: `param = [0, 0, 0]`, `grad = [1, 1, 1]`, `square_avg = [0, 1, 4]`, `lr = 0.1`, `alpha = 0.5`.

| quantity | el. 0 | el. 1 | el. 2 |
|---|---|---|---|
| `new_avg = 0.5 * old + 0.5 * 1` | `0.5` | `1` | `2.5` |
| `sqrt(new_avg)` | `0.7071` | `1` | `1.5811` |
| `new_param = -0.1 * 1 / sqrt` | `-0.1414` | `-0.1` | `-0.0632` |

Same gradient everywhere, but the element with the most squared-gradient history moves least.

## 5. Key idea: three placements the tests pin down

Each common slip moves one symbol, and each one is caught by a specific case:

| slip | formula | first case it fails | what you'd see |
|---|---|---|---|
| `alpha` on the new term | `(1 - alpha) * s + alpha * g²` | Example 1 | `0.88453` instead of `0.8` |
| `eps` inside the root | `g / sqrt(s + eps)` | tiny gradient, large eps | `0.299686` instead of `0.290911` |
| Adam's bias correction | `g / (sqrt(s / (1 - alpha)) + eps)` | Example 1 | `0.9` instead of `0.8` |

Two of these hide on specific cases. Swapped `alpha` passes Example 2 because `alpha = 0.5` makes both weights equal, and it passes "tiny gradient, large eps" because there $g^2 = 10^{-8}$ equals the old average, so any blend gives the same value. The tests that catch it are the others, especially "zero gradient", where the correct average decays to `[0.495, 0.198]` but the swapped one collapses to `[0.005, ...]`.

## 6. Plan before you code

```
g          = grad + weight_decay * param
new_avg    = alpha * square_avg + (1 - alpha) * g * g
new_param  = param - lr * g / (sqrt(new_avg) + eps)
return new_param, new_avg
```

## 7. Build it one piece at a time

**Step 1: the decayed gradient.** Same as problems 48 to 50.

```python
g = grad + weight_decay * param                          # (shape of param)
```

**Step 2: the moving average.** `alpha` multiplies the old state, `1 - alpha` the new evidence.

```python
square_avg = alpha * square_avg + (1 - alpha) * g * g   # (shape of param), elementwise
```

**Step 3: the step.**

```python
param = param - lr * g / (np.sqrt(square_avg) + eps)    # (shape of param)
```

The `eps` is a floor on the denominator, not a correction to the average. When an element's average is `0` its `g` is `0` too (unless `alpha` was 1, which the constraints exclude), so `0 / eps` gives no move. When the average is tiny but non-zero, as in "tiny gradient, large eps", `eps = 1e-3` dominates the `1e-4` root and caps the step.

## 8. Full solution

```python
# NumPy for elementwise sqrt; every line works on any array shape
import numpy as np


# one step of torch.optim.RMSprop with momentum=0, centered=False
def rmsprop_step(param, grad, square_avg, lr=0.01, alpha=0.99, eps=1e-8, weight_decay=0.0):
    g = grad + weight_decay * param    # L2 folded in first; the decayed gradient feeds the average
    square_avg = alpha * square_avg + (1 - alpha) * g * g  # EMA of g^2: alpha keeps the OLD average
    param = param - lr * g / (np.sqrt(square_avg) + eps)   # eps outside the root, and no bias correction
    return param, square_avg           # the judge checks both the parameters and the new average
```

## 9. How the test cases map to the code

| test case | expected `(new_param, new_square_avg)` | what it checks |
|---|---|---|
| Example 1 | `[0.8, -0.8]`, `[1, 1]` | first step is $\eta/\sqrt{1-\alpha}$; no bias correction |
| Example 2 | `[-0.1414, -0.1, -0.0632]`, `[0.5, 1, 2.5]` | more history, smaller step |
| default alpha with history | first element `-0.5551`, avg `0.1586` | defaults `alpha = 0.99`, `lr = 0.01` |
| tiny gradient, large eps | first element `0.2909` | `eps` outside the root |
| weight decay | `(3, 4)`, `new_param[0, 0] = -0.5883` | decay enters the average |
| zero gradient | `[1, -2]`, `[0.495, 0.198]` | the average still decays when the gradient is zero |
| first step, alpha 0.9 | `(4, 4)`, `new_param[0, 0] = -0.1186` | large gradients, `alpha = 0.9`: the first move is about `3.16 * lr` |

## 10. Complexity

$O(n)$ time and $O(n)$ memory per step for $n$ parameters: one state array, the same as momentum and Adagrad. RMSProp was the default for recurrent networks and for many reinforcement-learning setups (DQN used a variant), because those gradients change scale a lot over training and a forgetting denominator follows them. In most other places it has been replaced by Adam, which adds momentum and bias correction for one more state array.

## 11. If you got Wrong Answer

- **Example 1 gives `0.9` instead of `0.8`.** You applied bias correction, dividing the average by `1 - alpha`. That turns the first step into `lr` exactly. RMSProp doesn't correct.
- **Example 1 gives `0.88453`, but Example 2 passes.** You swapped the weights: `alpha` must multiply the old average. Example 2 uses `alpha = 0.5`, where swapping changes nothing.
- **Only "tiny gradient, large eps" fails (`0.299686` instead of `0.290911`).** `eps` is inside the square root.
- **"zero gradient" returns an unchanged average `[0.5, 0.2]`.** You skipped the update when the gradient is zero. The average must still decay by `alpha`.
- **Everything is off by a little.** Check the defaults: `alpha = 0.99`, `eps = 1e-8`, `lr = 0.01`.

## 12. Follow-ups an interviewer might ask

- *What does `centered=True` do?* It also tracks an EMA of $g$ itself, $\bar g$, and divides by $\sqrt{s - \bar g^2}$, an estimate of the gradient's variance rather than its raw second moment.
- *What does `momentum` do in PyTorch's RMSprop?* It keeps a buffer of the scaled step, $b = \mu b + g / (\sqrt{s} + \epsilon)$, and steps along it. With `momentum=0`, the case here, that reduces to the plain step.
- *Why not add bias correction?* You can, and then you're most of the way to Adam (problem 52). Without it, the first steps are about $1/\sqrt{1-\alpha}$ times larger, which in practice is often handled by a warmup schedule (problem 54).
- *How do you choose `alpha`?* It sets the memory, about $1/(1-\alpha)$ steps. Lower it if the gradient scale changes quickly; `0.9` forgets in about 10 steps, `0.99` in about 100.
