## 1. What the problem is really asking

Classical momentum (problem 48) computes the gradient where you are, then moves along the accumulated buffer. Nesterov's observation: you already know you're about to move by roughly $\mu b$, so measure the gradient at the point you're **about to reach** instead. If that point is past the bottom of a valley, its gradient points back, and the step is corrected before you overshoot.

In code you can't easily evaluate the gradient at a shifted point, because the gradient you're handed was computed at `param`. PyTorch uses an algebraic rewrite (Sutskever et al., 2013) that gives the same trajectory using only the gradient at the current parameters. Strip the story and the problem is **one line different from problem 48**: the buffer update is identical, and the step moves along $g + \mu b_t$ instead of $b_t$.

The judge compares both `new_param` and `new_buf`. The buffer is the same as classical momentum's, so the step is where all the bugs live.

## 2. Understand the inputs

| name | shape | what it is |
|---|---|---|
| `param` | any, e.g. `(2,)`, `(3, 4)`, `(5, 5)` | $\theta_{t-1}$ |
| `grad` | same as `param` | the gradient **at `param`** |
| `buf` | same as `param` | $b_{t-1}$; zeros on the first step |
| `lr` | scalar | $\eta$ |
| `momentum` | scalar in `[0, 1)`, default `0.9` | $\mu$ |
| `weight_decay` | scalar, default `0.0` | $\lambda$, plain L2 added to the gradient |

Easy to miss:

- **The look-ahead term uses the updated buffer**, $b_t$, not the one you were given.
- **The decayed gradient $g$ appears twice**: once in the buffer and once in the step. Using raw `grad` in the step is a bug that only the weight-decay case catches.
- **Return new arrays**; don't update `param` or `buf` in place.

## 3. The math

**The original Nesterov update** evaluates the gradient at a look-ahead point. Writing $v$ for the velocity and $x$ for the "real" parameters:

$$
v_t = \mu v_{t-1} + \nabla f\big(x_{t-1} - \eta\mu v_{t-1}\big), \qquad x_t = x_{t-1} - \eta v_t .
$$

**The change of variables.** Define the look-ahead point as the new parameter, $\theta_t = x_t - \eta\mu v_t$. Then the gradient in the $v$ update is exactly $\nabla f(\theta_{t-1})$, the gradient at the current parameter. Call it $g$. Now express $\theta_t$ in terms of $\theta_{t-1}$:

$$
\theta_t = x_t - \eta\mu v_t = (x_{t-1} - \eta v_t) - \eta\mu v_t .
$$

Substitute $x_{t-1} = \theta_{t-1} + \eta\mu v_{t-1}$:

$$
\theta_t = \theta_{t-1} + \eta\mu v_{t-1} - \eta v_t - \eta\mu v_t .
$$

From the velocity update, $\mu v_{t-1} = v_t - g$, so $\eta\mu v_{t-1} = \eta v_t - \eta g$. The $\eta v_t$ terms cancel:

$$
\theta_t = \theta_{t-1} - \eta\,(g + \mu v_t).
$$

Rename $v$ to $b$, add weight decay to $g$, and you have the statement's update:

$$
g = \nabla_\theta + \lambda\theta_{t-1}, \qquad b_t = \mu b_{t-1} + g, \qquad \theta_t = \theta_{t-1} - \eta\,(g + \mu b_t).
$$

You can confirm it numerically. On $f(x) = 5x^2$ from $x = 1$ with $\eta = 0.05$, $\mu = 0.9$: the original form's look-ahead points run `0.05, -0.4025, -0.404875, -0.203506, -0.011137`, and the reformulated parameter takes exactly the same values.

**Comparing the two steps.** Expand the Nesterov direction:

$$
g + \mu b_t = g + \mu(\mu b_{t-1} + g) = (1+\mu)\,g + \mu^2 b_{t-1}, \qquad\text{classical: } b_t = g + \mu b_{t-1}.
$$

Nesterov gives the fresh gradient weight $1 + \mu$ (1.9 at $\mu = 0.9$) instead of 1, and the history weight $\mu^2$ (0.81) instead of $\mu$ (0.9). Fresh information counts more, so when the gradient turns around, Nesterov turns faster. On the same $f(x) = 5x^2$ run for 30 steps, classical momentum is still swinging with amplitude up to `0.342` over the last 10 steps, while Nesterov is below `0.00014`.

## 4. Trace Example 2 by hand

`param = [0, 1, 2]`, `grad = [0.5, 0, -0.5]`, `buf = [1, 1, 1]`, `lr = 0.1`, `momentum = 0.5`. All `(3,)`.

| quantity | el. 0 | el. 1 | el. 2 |
|---|---|---|---|
| `g = grad` (no decay) | `0.5` | `0` | `-0.5` |
| `new_buf = 0.5 * buf + g` | `1` | `0.5` | `0` |
| `step = g + 0.5 * new_buf` | `1` | `0.25` | `-0.5` |
| `new_param = param - 0.1 * step` | `-0.1` | `0.975` | `2.05` |
| classical: `param - 0.1 * new_buf` | `-0.1` | `0.95` | `2.0` |

Element 0 happens to agree with classical momentum. Element 2 shows the difference clearly: the buffer has cancelled to `0`, so classical momentum doesn't move, but Nesterov still moves by `-lr * g`, following the fresh gradient. Element 1 has no gradient at all, and Nesterov moves only `0.025` where classical moves `0.05`, because history is weighted by $\mu^2$ rather than $\mu$.

**Example 1** is the first step: `buf = 0`, so `new_buf = g = [1, 2]` and the step is `g + 0.9 g = 1.9 g`. The parameters move by `0.19 * [1, 2]` to `[0.81, -2.38]`. Classical momentum would move by only `0.1 * [1, 2]`.

## 5. Key idea: the old buffer gives you classical momentum

A tempting bug is to use the incoming `buf` in the look-ahead term: `param - lr * (g + momentum * buf)`. But $g + \mu b_{t-1}$ *is* $b_t$, the classical step. So this bug isn't a slightly wrong Nesterov; it is exactly classical momentum. The ready-made `wrong_old_buffer.py` and `wrong_classical_step.py` produce identical outputs on every case (for example `0.9` instead of `0.81` for element 0 of Example 1). Write the buffer update first, then use the new value.

## 6. Plan before you code

```
g       = grad + weight_decay * param
new_buf = momentum * buf + g           # same as problem 48
step    = g + momentum * new_buf       # the only Nesterov line
new_param = param - lr * step
return new_param, new_buf
```

## 7. Build it one piece at a time

**Step 1: the effective gradient and the buffer**, exactly as in problem 48. Every array has the shape of `param`; the scalars broadcast.

```python
g = grad + weight_decay * param        # (shape of param)
buf = momentum * buf + g               # rebinds the local name; caller's array untouched
```

Rebinding `buf` with `=` builds a new array, so the caller's buffer is safe and every later line sees $b_t$.

**Step 2: the Nesterov step.**

```python
param = param - lr * (g + momentum * buf)   # buf is now b_t
```

Use `g`, not `grad`, inside the parentheses: PyTorch adds weight decay to the gradient once and uses that decayed gradient everywhere.

## 8. Full solution

```python
# NumPy arrays in, NumPy arrays out; every line is elementwise
import numpy as np


# one step of torch.optim.SGD(momentum=..., nesterov=True, dampening=0)
def nesterov_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    g = grad + weight_decay * param    # L2 folded into the gradient; this decayed g is used in buffer AND step
    buf = momentum * buf + g           # same running sum as classical momentum; now holds b_t (new array)
    param = param - lr * (g + momentum * buf)  # look-ahead step with the UPDATED buffer: (1+mu) g + mu^2 b_{t-1}
    return param, buf                  # the judge checks both; the buffer matches classical momentum's
```

## 9. How the test cases map to the code

| test case | expected `(new_param, new_buf)` | what it checks |
|---|---|---|
| Example 1 | `[0.81, -2.38]`, `[1, 2]` | first step: the step is `1.9 * g` |
| Example 2 | `[-0.1, 0.975, 2.05]`, `[1, 0.5, 0]` | the look-ahead uses the new buffer |
| random state | first element `0.5277`, buffer `1.6068` | default `momentum = 0.9` with history |
| zero momentum is plain SGD | `new_buf` equals `grad` | `momentum = 0` reduces to `param - lr * grad` |
| weight decay | `(3, 4)`, `new_param[0, 0] = -0.9208` | the decayed `g` is used in the step too |
| zero gradient, buffer coasts | `[0.872, -0.808]`, `[1.6, -2.4]` | with no gradient the step is `momentum * new_buf` |
| high momentum matrix | `(5, 5)`, `new_param[0, 0] = -0.0188` | `momentum = 0.99`, a large buffer |

## 10. Complexity

$O(n)$ time per step for $n$ parameters, and $O(n)$ memory for the one buffer: the same as classical momentum. Nesterov is free in production terms. The extra cost is one multiply-add per element, which is negligible next to the forward and backward passes. That's why PyTorch offers it as a flag rather than a separate optimizer.

## 11. If you got Wrong Answer

- **Example 1 gives `[0.9, -2.2]` instead of `[0.81, -2.38]`.** You stepped along the buffer (classical momentum), or you used the old buffer in the look-ahead term. Section 5 shows these are the same bug. Only "zero momentum is plain SGD" passes.
- **Everything passes except "weight decay" (`-0.9279` instead of `-0.9208`).** You put raw `grad` in the step: `param - lr * (grad + momentum * buf)`. Use the decayed `g` in both places.
- **"zero gradient, buffer coasts" gives `0.84` instead of `0.872`.** Same root cause as the first bullet: with `g = 0`, Nesterov's step is $\mu b_t$ and classical's is $b_t$.
- **The buffer is wrong too.** Check it against problem 48: `momentum * buf + g`, with no `(1 - momentum)` factor and no `lr` inside.

## 12. Follow-ups an interviewer might ask

- *Why is Nesterov's gradient "at the look-ahead point" if you only computed it at `param`?* Because of the change of variables in section 3: the stored `param` *is* the look-ahead point of the original method. The "real" point $x_t = \theta_t + \eta\mu b_t$ is never stored.
- *When does Nesterov help most?* On ill-conditioned problems with high momentum, where classical momentum overshoots and oscillates. On the $5x^2$ example, after 30 steps the remaining swing is about 2,500 times smaller (`0.00014` against `0.342`).
- *Does Adam have a Nesterov version?* Yes, NAdam applies the same look-ahead idea to Adam's first moment (problem 52 covers Adam).
- *What happens with `momentum = 0`?* Both terms collapse to $g$, so Nesterov, classical momentum and plain SGD coincide, which is what the "zero momentum is plain SGD" case checks.
