## 1. What the problem is really asking

Adam is the default optimizer for almost every neural network you'll train, and it is two earlier ideas glued together:

- **Momentum** (problem 48): keep a moving average of the gradient, $m$, and step along it, so noisy directions cancel and consistent ones build up.
- **RMSProp scaling** (problem 51): keep a moving average of the squared gradient, $v$, and divide by its root, so each parameter gets its own step size.

The one genuinely new piece is **bias correction**. Both averages start at zero, so for the first few hundred steps they are too small. Adam divides each by a known factor to undo that.

Strip the story and you are writing five elementwise lines with one scalar, `t`, that controls the correction. The judge compares three outputs: `new_param`, `new_m` and `new_v`. Note what is *not* returned: the bias-corrected $\hat m$ and $\hat v$. Those are temporaries, recomputed every step from the stored $m$, $v$ and `t`.

## 2. Understand the inputs

| name | shape | what it is |
|---|---|---|
| `param` | any, e.g. `(3,)`, `(4, 5)` | $\theta_{t-1}$ |
| `grad` | same as `param` | $g$, the gradient at `param` |
| `m` | same as `param` | $m_{t-1}$, first moment; zeros before step 1 |
| `v` | same as `param` | $v_{t-1}$, second moment; zeros before step 1 |
| `t` | int `>= 1` | the number of **this** step, used in $1 - \beta^t$ |
| `lr` | default `1e-3` | $\eta$ |
| `beta1`, `beta2` | defaults `0.9`, `0.999` | EMA weights on the **old** moments |
| `eps` | default `1e-8` | added after the square root |

Easy to miss:

- **`t` starts at 1.** On the first update $1 - \beta_1^1 = 0.1$. If you used `t = 0` you'd divide by zero.
- **Store the uncorrected moments.** Return `m` and `v`, not `m_hat` and `v_hat`. The next step needs the raw averages.
- **There is no weight decay here.** That's AdamW, problem 53.

## 3. The math

The update, all elementwise:

$$
m_t = \beta_1 m_{t-1} + (1-\beta_1)\,g, \qquad
v_t = \beta_2 v_{t-1} + (1-\beta_2)\,g^2,
$$

$$
\hat m_t = \frac{m_t}{1-\beta_1^t}, \qquad
\hat v_t = \frac{v_t}{1-\beta_2^t}, \qquad
\theta_t = \theta_{t-1} - \eta\,\frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon}.
$$

**Deriving the bias correction.** Unroll $m_t$ from $m_0 = 0$:

$$
m_t = (1-\beta_1)\sum_{k=1}^{t} \beta_1^{t-k} g_k .
$$

Suppose the gradients have a stationary mean, $\mathbb{E}[g_k] = \mu_g$. Take expectations:

$$
\mathbb{E}[m_t] = (1-\beta_1)\,\mu_g \sum_{k=1}^{t}\beta_1^{t-k} = (1-\beta_1)\,\mu_g\,\frac{1-\beta_1^t}{1-\beta_1} = (1-\beta_1^t)\,\mu_g .
$$

So $m_t$ is biased low by exactly the factor $1-\beta_1^t$, and dividing by it gives an unbiased estimate. The same algebra gives $\mathbb{E}[v_t] = (1-\beta_2^t)\,\mathbb{E}[g^2]$. The factors die out at different speeds:

| `t` | $1-\beta_1^t$ ($\beta_1 = 0.9$) | $1-\beta_2^t$ ($\beta_2 = 0.999$) | uncorrected ratio $\frac{1-\beta_1^t}{\sqrt{1-\beta_2^t}}$ |
|---|---|---|---|
| 1 | `0.1` | `0.001` | `3.1623` |
| 10 | `0.651322` | `0.009955` | `6.5279` |
| 100 | `0.999973` | `0.095208` | `3.2408` |
| 1000 | `1.0` | `0.632305` | `1.2576` |
| 5000 | `1.0` | `0.993279` | `1.0034` |

The last column is how much bigger the uncorrected step $m/\sqrt v$ is than the corrected one, for a constant gradient. Without correction the early steps are 3 to 6.5 times too large, and the effect lasts thousands of steps, because $\beta_2$ is so close to 1.

**The first step is $\eta \cdot \text{sign}(g)$.** At $t = 1$, $\hat m_1 = g$ and $\hat v_1 = g^2$, so $\hat m_1 / \sqrt{\hat v_1} = g / |g|$. Like Adagrad's first step (problem 50), the gradient's size doesn't matter, only its sign.

**The step is bounded.** Roughly, $|\hat m| \le \sqrt{\hat v}$ (a mean is at most the root-mean-square), so each element moves by at most about $\eta$. That is why Adam's `lr` is directly "how far each weight can move per step".

## 4. Trace the examples by hand

**Example 1**: `param = [1, -2, 3]`, `grad = [0.1, -0.2, 0.3]`, `m = v = 0`, `t = 1`, defaults otherwise.

| quantity | el. 0 | el. 1 | el. 2 |
|---|---|---|---|
| `m = 0.1 * g` | `0.01` | `-0.02` | `0.03` |
| `v = 0.001 * g²` | `1e-5` | `4e-5` | `9e-5` |
| `m_hat = m / 0.1` | `0.1` | `-0.2` | `0.3` |
| `v_hat = v / 0.001` | `0.01` | `0.04` | `0.09` |
| `m_hat / sqrt(v_hat)` | `1` | `-1` | `1` |
| `new_param = param - 1e-3 * that` | `0.999` | `-1.999` | `2.999` |

Every parameter moves by `lr = 0.001` against its gradient's sign. Without correction the ratio would be `m / sqrt(v) = 0.01 / 0.00316 = 3.16`, a step 3.16 times too big.

**Example 2**: `param = [0.5, 0.5]`, `grad = [1, -1]`, `m = [0.2, -0.1]`, `v = [0.04, 0.01]`, `t = 5`, `lr = 0.01`.

| quantity | el. 0 | el. 1 |
|---|---|---|
| `new_m = 0.9 m + 0.1 g` | `0.28` | `-0.19` |
| `new_v = 0.999 v + 0.001 g²` | `0.04096` | `0.01099` |
| `1 - 0.9^5`, `1 - 0.999^5` | `0.40951` | `0.00499` |
| `m_hat` | `0.683744` | `-0.463969` |
| `v_hat` | `8.2084` | `2.2024` |
| `m_hat / (sqrt(v_hat) + eps)` | `0.238652` | `-0.312637` |
| `new_param` | `0.497613` | `0.503126` |

Here the history dominates. `v_hat` (`8.2084`) is far bigger than `m_hat²` (about `0.47`), so the moments say this parameter's gradients have been large but inconsistent in sign. Adam trusts the direction less, and the step is only about a quarter of `lr` for element 0 and a third for element 1.

## 5. Key idea: `eps` outside the root, and when it shows

The placement $\sqrt{\hat v} + \epsilon$ matters only when $\sqrt{\hat v}$ is comparable to or smaller than $\epsilon$, that is, tiny gradients. In "tiny gradients", $g = 10^{-6}$, $\epsilon = 10^{-7}$, $t = 1$:

$$
\frac{\eta\,\hat m}{\sqrt{\hat v} + \epsilon} = \frac{10^{-3}\cdot 10^{-6}}{10^{-6} + 10^{-7}} = 9.09\times 10^{-4},
\qquad
\frac{\eta\,\hat m}{\sqrt{\hat v + \epsilon}} = \frac{10^{-9}}{3.16\times 10^{-4}} = 3.16\times 10^{-6}.
$$

Outside the root, `eps` is small next to $\sqrt{\hat v} = 10^{-6}$, so the step is still about 91% of `lr`. Inside the root, `eps` is added to $\hat v = 10^{-12}$ and swamps it, so the step shrinks almost 300 times. On the first element that is the difference between `-0.826859` and `-0.825953` (the parameter starts at `-0.82595`). With realistic gradients, $\hat v \gg \epsilon$ and the two placements agree to many digits, which is why only this case separates them.

## 6. Plan before you code

```
m      = beta1 * m + (1 - beta1) * grad
v      = beta2 * v + (1 - beta2) * grad^2
m_hat  = m / (1 - beta1^t)
v_hat  = v / (1 - beta2^t)
param  = param - lr * m_hat / (sqrt(v_hat) + eps)
return param, m, v              # raw moments, not the hats
```

## 7. Build it one piece at a time

**Step 1: update both moments.** These are the only stateful lines, and both use the raw `grad`.

```python
m = beta1 * m + (1 - beta1) * grad           # (shape of param)
v = beta2 * v + (1 - beta2) * grad * grad    # (shape of param), elementwise square
```

**Step 2: correct the bias.** `beta1 ** t` is a Python scalar, so the division broadcasts a single number over the whole array.

```python
m_hat = m / (1 - beta1 ** t)                 # (shape of param); scalar divisor
v_hat = v / (1 - beta2 ** t)                 # (shape of param)
```

Keep these in new names. Overwriting `m` with `m_hat` and returning it would store a corrected value that the next step corrects again.

**Step 3: the step.**

```python
param = param - lr * m_hat / (np.sqrt(v_hat) + eps)
```

`v_hat >= 0` always (it's a weighted sum of squares), so `np.sqrt` never sees a negative. With a zero gradient from zero moments, as in "zero gradient", `m_hat = 0` and the parameters don't move.

## 8. Full solution

```python
# NumPy for elementwise sqrt; every line works on any array shape
import numpy as np


# one bias-corrected Adam step (Kingma & Ba); t is this update's 1-based step number
def adam_step(param, grad, m, v, t, lr=1e-3, beta1=0.9, beta2=0.999, eps=1e-8):
    m = beta1 * m + (1 - beta1) * grad           # first moment: EMA of the gradient (momentum)
    v = beta2 * v + (1 - beta2) * grad * grad    # second moment: EMA of the squared gradient (RMSProp)
    m_hat = m / (1 - beta1 ** t)                 # undo the pull toward the zero start; scalar broadcast
    v_hat = v / (1 - beta2 ** t)                 # same for v, whose bias lasts far longer (beta2 near 1)
    param = param - lr * m_hat / (np.sqrt(v_hat) + eps)  # per-element step of at most about lr; eps outside root
    return param, m, v                           # store the RAW moments; the hats are recomputed next step
```

## 9. How the test cases map to the code

| test case | expected (first element of each output) | what it checks |
|---|---|---|
| Example 1 | `0.999`, `m = 0.01`, `v = 1e-5` | step 1: bias correction makes the move exactly `lr` |
| Example 2 | `0.497613`, `m = 0.28`, `v = 0.04096` | existing moments at `t = 5` |
| tiny gradients | `-0.826859` | `eps` outside the square root (custom `eps = 1e-7`) |
| zero gradient | param unchanged, moments `0` | no move from zero moments; `t = 3` is harmless |
| matrix param late step | `(4, 5)`, `-0.32562` | `t = 1000`: correction for `v` still matters |
| custom betas | `-0.27176`, `m = -0.1157` | `beta1`, `beta2` are parameters, not hard-coded |

## 10. Complexity

$O(n)$ time per step and $2n$ floats of state for $n$ parameters. In mixed-precision LLM training each parameter typically carries fp32 master weights plus fp32 `m` and `v`, 12 bytes of optimizer-side memory per parameter before activations. For a 7-billion-parameter model that is about 84 GB, more than the fp16 weights themselves. This is why ZeRO-style sharding splits optimizer state across GPUs, and why lower-memory optimizers (Adafactor, 8-bit Adam) exist.

## 11. If you got Wrong Answer

- **Example 1 gives `0.996838` instead of `0.999`.** You skipped bias correction, so the first step is $\sqrt{1000}/10 = 3.16$ times too large. Every case except "zero gradient" fails.
- **Only "tiny gradients" fails, with `-0.825953` instead of `-0.826859`.** `eps` is inside the root (`wrong_eps_inside_sqrt.py`). Section 5 shows why only tiny gradients expose it.
- **The parameters match but `new_m` is `10` times too big on step 1.** You returned `m_hat` instead of `m`.
- **`inf` or `nan` in the output at `t = 1`.** You computed `1 - beta1 ** (t - 1)`, which is `0` at `t = 1`, and NumPy divides the moments by zero. Use `t` as given.
- **"custom betas" fails but the rest pass.** You hard-coded `0.9` and `0.999` somewhere instead of using `beta1` and `beta2`.

## 12. Follow-ups an interviewer might ask

- *How do you add weight decay to Adam?* Not by adding $\lambda\theta$ to the gradient, because then $\sqrt{\hat v}$ rescales the decay per parameter. Decouple it and shrink the weights directly: that's AdamW (problem 53).
- *Why is `beta2` so much closer to 1 than `beta1`?* The second moment sets the step scale and needs a stable, long-memory estimate (about 1,000 steps). The first moment is the direction and should react within about 10 steps.
- *Why does Adam usually need warmup?* Early $\hat v$ is estimated from very few gradients and can be badly off, so early steps are unreliable even with bias correction. A warmup ramp on `lr` (problem 54) keeps those steps small.
- *What is AMSGrad?* It keeps the running maximum of $\hat v$ and divides by that, so the effective step can never grow. It fixes a convergence counterexample for Adam but rarely matters in practice.
- *What happens when a gradient is clipped first?* Clipping (problem 55) rescales `grad` before it enters `m` and `v`, so a single spike doesn't inflate `v` for the next thousand steps.
