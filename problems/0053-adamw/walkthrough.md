## 1. What the problem is really asking

Weight decay means "shrink every weight a little each step, toward zero". With plain SGD you get that by adding $\lambda\theta$ to the gradient (L2 regularization), and the two ideas are the same thing (problem 48). With Adam they are **not** the same. Anything you add to the gradient goes into $m$ and $v$ and then gets divided by $\sqrt{\hat v}$, so the decay a parameter actually receives depends on its gradient history. Loshchilov and Hutter's fix, AdamW, is to take the decay out of the gradient and apply it to the weights directly.

Strip the story and this is **problem 52 plus one line at the top**: `param = param * (1 - lr * weight_decay)`, then an ordinary Adam step on the raw gradient. What you have to get right is where that line goes (first, acting on $\theta_{t-1}$), what it multiplies by (`lr * weight_decay`, as PyTorch does), and what it must not touch (`m` and `v`). The judge compares `new_param`, `new_m` and `new_v`.

## 2. Understand the inputs

| name | shape | what it is |
|---|---|---|
| `param` | any, e.g. `(3,)`, `(4, 5)` | $\theta_{t-1}$ |
| `grad` | same | the raw gradient $g$; never decayed |
| `m`, `v` | same | Adam's moments, zeros before step 1 |
| `t` | int `>= 1` | this step's number, for bias correction |
| `lr` | default `1e-3` | $\eta$; also scales the decay |
| `beta1`, `beta2` | defaults `0.9`, `0.999` | moment EMA weights |
| `eps` | default `1e-8` | outside the square root |
| `weight_decay` | default `1e-2` | $\lambda$; note the default is **not** zero |

Easy to miss:

- **The default `weight_decay` is `0.01`.** "default decay late step" leaves it out and relies on it.
- **`m` and `v` are computed from the raw `grad`**, so they come out identical to plain Adam's. If your `new_m` differs from Adam's on the same inputs, decay leaked into the gradient.
- **The decay multiplies `param` before the Adam step**, not after.

## 3. The math

The update, in the statement's order:

$$
\theta' = \theta_{t-1}(1 - \eta\lambda), \qquad
m_t = \beta_1 m_{t-1} + (1-\beta_1) g, \qquad
v_t = \beta_2 v_{t-1} + (1-\beta_2) g^2,
$$

$$
\hat m_t = \frac{m_t}{1-\beta_1^t}, \qquad \hat v_t = \frac{v_t}{1-\beta_2^t}, \qquad
\theta_t = \theta' - \eta\,\frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon}.
$$

Expanding the first line, $\theta' = \theta_{t-1} - \eta\lambda\,\theta_{t-1}$. That is exactly an SGD step on the penalty $\frac{\lambda}{2}\lVert\theta\rVert^2$, whose gradient is $\lambda\theta$, taken *outside* Adam's rescaling.

**Why L2-in-the-gradient goes wrong under Adam.** Write $\tilde g = g + \lambda\theta$ for the L2 gradient. Adam's step is roughly $\eta\,\tilde g / \sqrt{\hat v}$, where $\sqrt{\hat v}$ is about the root-mean-square of $\tilde g$. So the decay part of the step is about

$$
\eta\,\frac{\lambda\theta}{\sqrt{\hat v}} .
$$

Take two weights with $\theta = 1$ and $\lambda = 0.01$. If one has gradients of RMS size `100`, its decay is $0.0001\,\eta$ per step. If the other has gradients of RMS size `0.01`, its decay is $1.0\,\eta$, ten thousand times more. The weights that see big gradients are barely regularized, and the quiet ones are crushed. With AdamW both get exactly $\eta\lambda\theta = 0.01\,\eta$.

**Why the decay is scaled by `lr`.** The paper writes the decay with a separate schedule multiplier. PyTorch folds it into `lr`, so when a schedule lowers the learning rate (problem 54), the decay is annealed with it. Without the `lr`, `weight_decay = 0.01` would remove 1% of every weight every step regardless of the schedule.

## 4. Trace the examples by hand

**Example 1**: `param = [1, -2, 3]`, `grad = [0.1, -0.2, 0.3]`, `m = v = 0`, `t = 1`, `lr = 0.1`, `weight_decay = 0.5`.

| quantity | el. 0 | el. 1 | el. 2 |
|---|---|---|---|
| decay factor `1 - 0.1 * 0.5` | `0.95` | `0.95` | `0.95` |
| `θ' = param * 0.95` | `0.95` | `-1.9` | `2.85` |
| `new_m = 0.1 * g` | `0.01` | `-0.02` | `0.03` |
| `new_v = 0.001 * g²` | `1e-5` | `4e-5` | `9e-5` |
| `m_hat / sqrt(v_hat)` (step 1) | `1` | `-1` | `1` |
| `new_param = θ' - 0.1 * that` | `0.85` | `-1.8` | `2.75` |

The decay removes 5% of each weight, then Adam moves each by `lr = 0.1` against its gradient's sign. The moments are exactly plain Adam's.

Compare with L2 in the gradient: $\tilde g = g + 0.5\,\theta = [0.6, -1.2, 1.8]$. Its sign matches $g$'s everywhere, and on step 1 Adam moves by `lr * sign`, so you get `[0.9, -1.9, 2.9]`: the decay has disappeared completely. That's the rescaling problem at its most extreme.

**Example 2**: `param = [2, -2]`, `grad = [0, 0]`, `m = v = 0`, `t = 1`, `lr = 0.1`, `weight_decay = 0.1`. The decay factor is `0.99`, so $\theta' = [1.98, -1.98]$. With a zero gradient, `m_hat = 0` and the Adam step is zero, so `new_param = [1.98, -1.98]`. Under L2-in-the-gradient, $\tilde g = 0.1\,\theta = [0.2, -0.2]$, and Adam's first step turns that small pull into a full `lr`-sized move, giving `[1.9, -1.9]`.

## 5. Key idea: decay first, on the old weights

There are two orderings that both "apply decay and an Adam step". The problem fixes decay first:

$$
\theta_t = \theta_{t-1}(1-\eta\lambda) - \eta\,u_t \quad\text{(correct)}
\qquad\text{vs}\qquad
\theta_t = \big(\theta_{t-1} - \eta\,u_t\big)(1-\eta\lambda) \quad\text{(decay after)},
$$

where $u_t = \hat m_t / (\sqrt{\hat v_t} + \epsilon)$. They differ by $\eta^2\lambda\,u_t$: the decay-after version also shrinks the Adam step. In Example 1 that's $0.1 \times 0.05 \times 1 = 0.005$, so element 0 comes out `0.855` instead of `0.85`. The difference scales with $\eta^2\lambda$, so at `lr = 3e-4` it's around $10^{-9}$ and invisible: "default decay late step" passes even with the wrong order. The cases with large `lr` catch it.

## 6. Plan before you code

```
param = param * (1 - lr * weight_decay)          # decoupled decay on θ_{t-1}
m     = beta1 * m + (1 - beta1) * grad           # raw grad
v     = beta2 * v + (1 - beta2) * grad^2
m_hat = m / (1 - beta1^t);  v_hat = v / (1 - beta2^t)
param = param - lr * m_hat / (sqrt(v_hat) + eps)
return param, m, v
```

## 7. Build it one piece at a time

**Step 1: the decay.** A scalar factor broadcast over the whole array. The constraint `lr * weight_decay < 1` keeps the factor positive, so the decay never flips a weight's sign.

```python
param = param * (1 - lr * weight_decay)          # (shape of param); new array
```

**Step 2: the moments, from the raw gradient.**

```python
m = beta1 * m + (1 - beta1) * grad               # (shape of param)
v = beta2 * v + (1 - beta2) * grad * grad        # (shape of param)
```

**Step 3: bias correction and the step, exactly as in problem 52.**

```python
m_hat = m / (1 - beta1 ** t)
v_hat = v / (1 - beta2 ** t)
param = param - lr * m_hat / (np.sqrt(v_hat) + eps)
```

Because step 1 rebinds `param`, the subtraction in step 3 acts on the decayed $\theta'$, which is the order the statement asks for.

## 8. Full solution

```python
# NumPy for elementwise sqrt; every line works on any array shape
import numpy as np


# one step of torch.optim.AdamW (amsgrad=False): Adam plus decoupled weight decay
def adamw_step(param, grad, m, v, t, lr=1e-3, beta1=0.9, beta2=0.999, eps=1e-8, weight_decay=1e-2):
    param = param * (1 - lr * weight_decay)      # decay theta_{t-1} directly, scaled by lr; never enters m or v
    m = beta1 * m + (1 - beta1) * grad           # first moment from the RAW gradient, identical to Adam's
    v = beta2 * v + (1 - beta2) * grad * grad    # second moment, also undecayed
    m_hat = m / (1 - beta1 ** t)                 # bias correction for the zero start (t is 1-based)
    v_hat = v / (1 - beta2 ** t)                 # same for v
    param = param - lr * m_hat / (np.sqrt(v_hat) + eps)  # ordinary Adam step applied to the decayed weights
    return param, m, v                           # raw moments, so the next step can correct them again
```

## 9. How the test cases map to the code

| test case | expected (first element of `new_param`) | what it checks |
|---|---|---|
| Example 1 | `0.85` (vector `[0.85, -1.8, 2.75]`) | decay then Adam; L2 would give `0.9` |
| Example 2 | `1.98` (vector `[1.98, -1.98]`) | zero gradient: only the decay acts |
| default decay late step | `0.1045`, shape `(4, 5)` | `weight_decay` defaults to `0.01`; `t = 500` |
| strong decay, large lr | `2.2754` | `lr * weight_decay = 0.02`; order of decay and step matters |
| zero decay equals Adam | `0.3249` | with `weight_decay = 0`, AdamW is Adam |
| custom betas | `0.6335` | `beta1 = 0.8`, `beta2 = 0.95` are used |
| tiny gradients | `-0.0135` | decay dominates when the gradient is `1e-6` |

## 10. Complexity

$O(n)$ time per step and $2n$ floats of state, the same as Adam (problem 52). The decay needs no extra memory. AdamW is the standard optimizer for transformers: BERT, GPT-style LLMs and ViTs are all trained with it, usually with `weight_decay` around `0.1` and a warmup-plus-cosine schedule (problem 54). In practice you also exclude biases and normalization weights from decay, which in PyTorch means two parameter groups with different `weight_decay` values.

## 11. If you got Wrong Answer

- **Example 1 gives `0.9`, Example 2 gives `1.9`.** You added `weight_decay * param` to the gradient (Adam with L2). Your `new_m` and `new_v` are wrong too, because the decay leaked into them.
- **Example 1 gives `0.4`, Example 2 gives `1.8`.** You decayed by `(1 - weight_decay)` without `lr`. That removes 50% of each weight in Example 1.
- **Example 1 gives `0.855`, Example 2 passes.** You decayed after the Adam step, which also shrinks the step (section 5). Example 2 can't see it because its step is zero.
- **"default decay late step" fails, everything else passes.** Check the signature default `weight_decay=1e-2`.
- **"zero decay equals Adam" fails.** The Adam part itself is off; compare against problem 52's walkthrough (bias correction, `eps` placement).

## 12. Follow-ups an interviewer might ask

- *Is AdamW with `weight_decay = λ` the same as Adam with L2 `λ`?* No. Section 3 shows the effective decay under L2 is divided by $\sqrt{\hat v}$, so it varies per parameter by orders of magnitude. With SGD the two coincide (problem 48).
- *Which parameters should you not decay?* Biases and LayerNorm or RMSNorm gains (problems 41 and 74). Pulling a norm's scale toward zero fights the normalization, and biases have too few parameters to overfit.
- *How does the schedule interact with decay?* Since PyTorch multiplies decay by `lr`, a cosine schedule (problem 54) anneals both together. If you change `lr` by 10×, the effective decay changes by 10× too, so retune `weight_decay` when you retune `lr`.
- *What would `amsgrad=True` change?* It keeps a running maximum of $v$ and uses that in the denominator. The decay line is unchanged.
