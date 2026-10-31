## 1. What the problem is really asking

Plain gradient descent moves by `-lr * grad` and forgets everything after each step. Momentum adds **one piece of state**, a buffer the same shape as the parameters, that remembers a decaying sum of past gradients. The parameters then move along the buffer instead of along the latest gradient.

Strip the story and this is three elementwise lines: add weight decay to the gradient, fold the result into the buffer, step along the buffer. The difficulty is not the arithmetic. It is matching **one exact convention** out of several that are all called "momentum". The problem pins it down: PyTorch's `torch.optim.SGD` with `dampening=0` and `nesterov=False`.

The judge compares both outputs, `new_param` **and** `new_buf`. That matters, because two of the common conventions produce identical parameters with a different buffer, and only the buffer comparison tells them apart.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `param` | any, e.g. `(3,)` or `(5, 5)` | $\theta_{t-1}$, the current parameters | decayed, then stepped |
| `grad` | same as `param` | $\nabla_\theta$ at `param` | the raw gradient |
| `buf` | same as `param` | $b_{t-1}$, the buffer from the last step; zeros on step 1 | decayed by `momentum` and added to |
| `lr` | scalar | $\eta$ | applied only when stepping |
| `momentum` | scalar in `[0, 1)` | $\mu$, default `0.9` | how much of the old buffer survives |
| `weight_decay` | scalar `>= 0` | $\lambda$, default `0.0` | L2 penalty folded into the gradient |

Easy to miss:

- **Defaults matter.** Several cases leave out `momentum` and rely on `0.9`. Keep the signature defaults exactly.
- **Weight decay enters the buffer.** It is added to the gradient *before* the buffer update, so the buffer accumulates it too. Example 3 has a zero gradient and still gets a non-zero buffer.
- **No in-place updates.** `buf *= momentum` would change the caller's array. Build new arrays.

## 3. The math

The update, from the statement:

$$
g = \nabla_\theta + \lambda\,\theta_{t-1}, \qquad
b_t = \mu\, b_{t-1} + g, \qquad
\theta_t = \theta_{t-1} - \eta\, b_t .
$$

**Where the weight-decay term comes from.** L2 regularization adds $\frac{\lambda}{2}\lVert\theta\rVert^2$ to the loss. Its gradient is $\lambda\theta$, so the regularized gradient is $\nabla_\theta + \lambda\theta$. That is the $g$ above: weight decay here is nothing but a modified gradient.

**What the buffer holds.** Unroll the recursion from $b_0 = 0$:

$$
b_t = g_t + \mu g_{t-1} + \mu^2 g_{t-2} + \dots + \mu^{t-1} g_1 = \sum_{k=0}^{t-1} \mu^k g_{t-k}.
$$

It is a geometrically weighted **sum** of gradients, with recent ones weighted most. If the gradient is a constant $g$, this is a geometric series:

$$
b_t = g\,\frac{1 - \mu^t}{1 - \mu} \;\longrightarrow\; \frac{g}{1-\mu}.
$$

With $\mu = 0.9$ the buffer grows `1, 1.9, 2.71, ...`, reaches `6.5132` after 10 steps and `9.9485` after 50, approaching 10. So along a direction where the gradient stays consistent, momentum gives up to a $\frac{1}{1-\mu} = 10\times$ larger step. Along a direction where the gradient flips sign every step, the terms cancel: with gradients `+1, -1, +1, ...` the buffer runs `1, -0.1, 0.91, -0.181, ...` and stays small. That pair of behaviours, acceleration along a valley and damping across it, is the whole reason momentum exists.

**The CS231n form.** Some course notes write $v_t = \mu v_{t-1} - \eta g$, $\theta_t = \theta_{t-1} + v_t$. If $\eta$ is constant, $v_t = -\eta\, b_t$ by induction: $v_t = \mu(-\eta b_{t-1}) - \eta g = -\eta(\mu b_{t-1} + g) = -\eta b_t$. So the parameters are identical but the stored buffer is $-\eta$ times PyTorch's. The two diverge once $\eta$ changes. On $f(x) = x^2$ from $x = 1$ with `lr = 0.1` for three steps, both reach `0.062`. Drop `lr` to `0.01` for step 4 and PyTorch moves to `0.02494`, while the CS231n form jumps to `-0.29744`, because its buffer still carries the old learning rate baked in. That is why the problem insists on PyTorch's buffer.

**Why no $(1-\mu)$.** Adam's first moment is an exponential moving average, $m_t = \beta m_{t-1} + (1-\beta) g$, which is an *average* and stays at the scale of $g$ (problem 52). PyTorch's momentum buffer is a *sum* and grows to $g/(1-\mu)$. Mixing the two up changes the effective step size by a factor of 10 at $\mu = 0.9$.

## 4. Trace the examples by hand

**Example 2**: `param = [0.5, 0.5]`, `grad = [1, -1]`, `buf = [2, 1]`, `lr = 0.1`, `momentum = 0.5`, no decay. All arrays are `(2,)`.

| quantity | element 0 | element 1 |
|---|---|---|
| `g = grad + 0 * param` | `1` | `-1` |
| `momentum * buf` | `1` | `0.5` |
| `new_buf = momentum * buf + g` | `2` | `-0.5` |
| `lr * new_buf` | `0.2` | `-0.05` |
| `new_param = param - lr * new_buf` | `0.3` | `0.55` |

Element 1 is the interesting one. The gradient says "go up" (`-grad` is `+1`), but the history says "go down" (`buf = 1`). The history wins partly: the buffer shrinks to `-0.5`, so the parameter moves up by only `0.05`.

**Example 3**: `param = [2, -1]`, `grad = [0, 0]`, `buf = [0, 0]`, `lr = 0.5`, `momentum = 0.9`, `weight_decay = 0.1`.

| quantity | element 0 | element 1 |
|---|---|---|
| `g = 0 + 0.1 * param` | `0.2` | `-0.1` |
| `new_buf = 0.9 * 0 + g` | `0.2` | `-0.1` |
| `new_param = param - 0.5 * new_buf` | `1.9` | `-0.95` |

With no gradient at all, weight decay alone pulls each parameter 5% toward zero (`lr * weight_decay = 0.05`), and the buffer records that pull so it will keep coasting next step.

## 5. Plan before you code

```
g       = grad + weight_decay * param        # L2 folded into the gradient
new_buf = momentum * buf + g                 # running sum, no (1 - momentum)
new_param = param - lr * new_buf             # lr applied outside the buffer
return new_param, new_buf
```

The order is forced: the step needs `new_buf`, and `new_buf` needs `g`.

## 6. Build it one piece at a time

**Step 1: the effective gradient.** Every array here has the shape of `param`, and the scalars `weight_decay`, `momentum` and `lr` broadcast against them, so the same code works for `(3,)` and `(5, 5)`.

```python
g = grad + weight_decay * param        # (shape of param); scalar * array broadcasts
```

**Step 2: the buffer.** Use plain assignment so you create a new array instead of writing into the caller's `buf`.

```python
new_buf = momentum * buf + g           # (shape of param)
```

`buf *= momentum; buf += g` gives the same numbers but mutates the input, which the statement forbids.

**Step 3: the step.**

```python
new_param = param - lr * new_buf       # (shape of param)
```

Note that `new_buf`, not `buf`, appears here. Using the old buffer would lag one step behind the gradient you were just given.

## 7. Full solution

```python
# NumPy arrays in, NumPy arrays out; everything below is elementwise
import numpy as np


# one step of torch.optim.SGD(momentum=..., dampening=0, nesterov=False)
def sgd_momentum_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    g = grad + weight_decay * param    # L2 penalty's gradient is weight_decay * param; it feeds the buffer too
    buf = momentum * buf + g           # decayed running SUM of gradients (no 1 - momentum); new array, input untouched
    param = param - lr * buf           # lr applied outside the buffer, so a schedule change takes effect at once
    return param, buf                  # the judge checks both the new parameters and the PyTorch-style buffer
```

## 8. How the test cases map to the code

| test case | expected `(new_param, new_buf)` | what it checks |
|---|---|---|
| Example 1 | `[0.95, -1.9, 2.8]`, `[0.5, -1, 2]` | first step: `buf` is zero, so `new_buf = grad` |
| Example 2 | `[0.3, 0.55]`, `[2, -0.5]` | an existing buffer is decayed by `momentum = 0.5` and added to |
| Example 3 | `[1.9, -0.95]`, `[0.2, -0.1]` | weight decay enters the buffer even with a zero gradient |
| nonzero buffer, default momentum | first element `-0.3032`, buffer `-0.0887` | `momentum` defaults to `0.9` |
| zero momentum is plain SGD | `new_buf` equals `grad` exactly | `momentum = 0` reduces to `param - lr * grad` |
| weight decay with history | `(3, 4)` arrays, `new_buf[0, 0] = 0.6525` | decay, history and a 2-D shape at once |
| matrix param | `(5, 5)`, `momentum = 0.99`, `lr = 1e-3` | high momentum, larger gradients |
| zero gradient, momentum coasts | `[0.964, 2.036]`, `[0.36, -0.36]` | with no gradient, the parameters still move along the decayed buffer |

## 9. Complexity

For $n$ parameters a step is $O(n)$ time: three elementwise passes. Memory is one extra buffer of $n$ floats, which is the optimizer state. For a 7-billion-parameter model in fp32 that buffer is 28 GB on its own. That is why momentum SGD (one state array) is cheaper to train with than Adam (two state arrays, problem 52), and why large-scale training shards optimizer state across devices.

## 10. If you got Wrong Answer

- **`new_buf[0]` is `-0.05` in Example 1 instead of `0.5`.** You used the CS231n buffer, `momentum * buf - lr * g`. Your parameters move the same way on this first step, but the buffer is `-lr` times PyTorch's. Every case fails on it.
- **`new_param[0]` is `0.995` in Example 1 instead of `0.95`.** You wrote an EMA, `momentum * buf + (1 - momentum) * g`. On the first step that scales the move by `0.1`. "zero momentum is plain SGD" and "zero gradient, momentum coasts" still pass, which is why it can survive a quick test.
- **Example 3 returns a zero buffer.** You added weight decay to the step but not to the buffer (`param - lr * (buf + weight_decay * param)`). Only Example 3 and "weight decay with history" catch it, because every other case has `weight_decay = 0`.
- **The caller's `buf` changed after the call.** You used `*=` or `+=`. The judge passes copies, so it won't flag this, but the statement forbids it and a training loop that keeps its own reference to `buf` would see it change twice. Use plain assignment so you return new arrays.

## 11. Follow-ups an interviewer might ask

- *What does Nesterov momentum change?* Only the step: it moves along $g + \mu b_t$ instead of $b_t$, which approximates evaluating the gradient at the point you are about to reach. The buffer update is identical (problem 49).
- *What is `dampening` in PyTorch?* It replaces $b_t = \mu b_{t-1} + g$ with $b_t = \mu b_{t-1} + (1 - d) g$. With $d = \mu$ you get the EMA form. The default is $0$.
- *How do you pick `lr` when you add momentum?* The steady-state step is $\eta / (1 - \mu)$ times the gradient, so when you go from no momentum to $\mu = 0.9$, divide `lr` by about 10 to keep the same effective step.
- *Is weight decay the same as L2 for momentum SGD?* Here, yes, because decay is added to the gradient. For Adam they differ, and decoupled weight decay (AdamW, problem 53) is the fix.
