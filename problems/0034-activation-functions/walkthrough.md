## 1. What the problem is really asking

Every neural network layer is a linear map followed by a nonlinearity. Backpropagation needs two things from that nonlinearity: its value on the forward pass, and its derivative on the backward pass. This problem asks for both, for five activations, in one function.

Under the story, it's **ten elementwise array expressions**. There is no loop, no reduction and no shape change: every output has the shape of `x`, whatever that is (`(3,)`, `(2, 2)`, `(2, 3, 4)`). The work is in getting three things exactly right:

- the **derivatives**, especially GELU's, which you derive yourself;
- the **convention at `x = 0`** for ReLU and Leaky ReLU, where the derivative doesn't exist mathematically;
- a sigmoid that stays **finite and warning-free** at `x = ±1000`.

The judge compares all ten arrays with `rtol=1e-6`.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `x` | float array, any shape, values in `[-1000, 1000]` | every formula is applied elementwise |
| `alpha` | Leaky ReLU slope for `x <= 0`, default `0.01` | `alpha * x` on the negative side |
| return | dict of 10 arrays, each shaped like `x` | keys `sigmoid`, `d_sigmoid`, ..., `d_gelu` |

The details that are easy to miss:

- **`d_relu(0) = 0` and `d_leaky_relu(0) = alpha`.** The mask is `x > 0`, strictly. The "exact zeros" case includes `0.0`, `-0.0`, `1e-12` and `-1e-12`; only `1e-12` gets slope 1.
- **The GELU here is the tanh approximation**, and you differentiate *that* formula, not the erf-based GELU.
- **`x` can have any number of dimensions.** Write nothing that assumes 1-D. Elementwise NumPy operations don't care.

## 3. The math

**Sigmoid.** $\sigma(x) = (1 + e^{-x})^{-1}$. By the chain rule,

$$\sigma'(x) = -(1 + e^{-x})^{-2} \cdot (-e^{-x}) = \frac{e^{-x}}{(1 + e^{-x})^2} = \underbrace{\frac{1}{1 + e^{-x}}}_{\sigma(x)} \cdot \underbrace{\frac{e^{-x}}{1 + e^{-x}}}_{1 - \sigma(x)}.$$

So $\sigma' = \sigma(1 - \sigma)$, written in terms of the **output** $s = \sigma(x)$. Its maximum is $0.25$ at $x = 0$.

**Tanh.** $\tanh x = \sinh x / \cosh x$. The quotient rule gives

$$\tanh'(x) = \frac{\cosh^2 x - \sinh^2 x}{\cosh^2 x} = 1 - \tanh^2 x.$$

**ReLU and Leaky ReLU.** These are piecewise linear. The slope is $1$ on $x > 0$ and $0$ (ReLU) or $\alpha$ (leaky) on $x < 0$. At $x = 0$ the left and right slopes differ, so there's no derivative; the problem picks the left slope, as PyTorch does.

**GELU (tanh approximation).** With $c = \sqrt{2/\pi}$, $u(x) = c\,(x + 0.044715\,x^3)$ and $t = \tanh u$:

$$\operatorname{gelu}(x) = \tfrac12\, x\,(1 + t).$$

It's a product of $\tfrac12 x$ and $(1 + t)$, so apply the product rule:

$$\operatorname{gelu}'(x) = \tfrac12 (1 + t) + \tfrac12 x \cdot \frac{dt}{dx}.$$

Then the chain rule through $t = \tanh u$:

$$\frac{dt}{dx} = (1 - t^2)\,\frac{du}{dx}, \qquad \frac{du}{dx} = c\,(1 + 3 \cdot 0.044715\, x^2).$$

Putting it together:

$$\boxed{\operatorname{gelu}'(x) = \tfrac12 (1 + t) + \tfrac12\, x\, (1 - t^2)\, c\, (1 + 0.134145\, x^2)}$$

At $x = 0$ the second term vanishes and $\operatorname{gelu}'(0) = 0.5$. For $x \to +\infty$, $t \to 1$ and the derivative goes to $1$; for $x \to -\infty$ it goes to $0$. In between it overshoots: about $1.1277$ at $x = 1.5$ and about $-0.1277$ at $x = -1.5$. GELU is not monotonic.

## 4. Key idea: a sigmoid that never overflows

The textbook `1 / (1 + np.exp(-x))` at `x = -1000` computes `np.exp(1000)`, which overflows to `inf` with a `RuntimeWarning`. The result `1 / inf = 0` happens to be right, but the warning is a sign that some other formula built the same way (say, `np.exp(-x) / (1 + np.exp(-x))`) will produce `inf / inf = nan`.

The fix is to only ever exponentiate a **non-positive** number. Let $e = e^{-|x|} \in (0, 1]$:

- for $x \ge 0$, $e = e^{-x}$ and $\sigma(x) = 1/(1 + e)$;
- for $x < 0$, $e = e^{x}$, and multiplying top and bottom of $1/(1 + e^{-x})$ by $e^{x}$ gives $\sigma(x) = e/(1 + e)$.

Both branches use the same `e`, which is never more than 1, so nothing overflows:

```python
e = np.exp(-np.abs(x))                                  # same shape as x, all in (0, 1]
s = np.where(x >= 0, 1.0 / (1.0 + e), e / (1.0 + e))    # same shape as x
```

`np.where` evaluates **both** branches for every element and then picks one. That's fine here, because both branches are safe everywhere. It would not be fine if one branch could overflow, which is the whole reason the naive version can't be fixed by wrapping it in `np.where`.

Tanh needs no trick: `np.tanh` is stable for any input. The derivative $1 - t^2$ goes to exactly 0 at $|x| = 50$ in float64.

## 5. Trace an example by hand

**Example 1:** `x = [-2, 0, 2]`, `alpha = 0.01`. Every array below has shape `(3,)`.

| quantity | `x = -2` | `x = 0` | `x = 2` |
|---|---|---|---|
| `s = sigmoid` | 0.1192 | 0.5 | 0.8808 |
| `d_sigmoid = s(1-s)` | 0.105 | 0.25 | 0.105 |
| `t = tanh` | -0.964 | 0 | 0.964 |
| `d_tanh = 1 - t²` | 0.0707 | 1 | 0.0707 |
| `pos = x > 0` | False | False | True |
| `d_relu` | 0 | **0** | 1 |
| `d_leaky_relu` | 0.01 | **0.01** | 1 |
| `u` | -1.88119 | 0 | 1.88119 |
| `tu = tanh(u)` | -0.95460 | 0 | 0.95460 |
| `du` | 1.22601 | 0.79788 | 1.22601 |
| `0.5(1 + tu)` | 0.02270 | 0.5 | 0.97730 |
| `0.5·x·(1 - tu²)·du` | -0.10880 | 0 | 0.10880 |
| `d_gelu` (sum of the two) | -0.0861 | 0.5 | 1.0861 |
| `gelu` | -0.0454 | 0 | 1.9546 |

The last three rows show why the product rule matters. At `x = 2`, the term you'd drop by treating `x` as a constant is `0.10880`, about 10% of the answer. At `x = -2` it's larger than the first term and flips the sign of the derivative.

A finite-difference check, $(g(x+h) - g(x-h))/(2h)$ with $h = 10^{-6}$, gives `-0.08609926` at `x = -2` and `1.08609926` at `x = 2`, matching. That check is worth running whenever you derive a gradient by hand (problem 46, numerical-gradient-check).

## 6. Plan before you code

```
x  = x as a float array                      # any shape
s  = stable sigmoid(x)
t  = tanh(x)
pos = x > 0                                  # boolean, same shape
u, tu, du = GELU pieces
return the ten arrays, each built from s, t, pos, tu, du
```

| output | formula | why this form |
|---|---|---|
| `d_sigmoid` | `s * (1 - s)` | reuses the forward value, no extra `exp` |
| `d_tanh` | `1 - t * t` | reuses the forward value |
| `relu`, `d_relu` | `np.where(pos, x, 0)`, `pos.astype(float)` | one mask gives the `x = 0` convention for both |
| `leaky_relu`, `d_leaky_relu` | `np.where(pos, x, alpha * x)`, `np.where(pos, 1, alpha)` | the same mask |
| `d_gelu` | product rule + chain rule | section 3 |

## 7. Build it one piece at a time

**Step 1: make `x` a float array.**

```python
x = np.asarray(x, dtype=float)    # any shape, float64
```

If someone passes an integer array, `alpha * x` and the divisions still work, but `np.where(pos, x, 0.0)` would mix dtypes. Casting once at the top avoids surprises.

**Step 2: the forward values you'll reuse.**

```python
s = _sigmoid(x)    # same shape as x, in [0, 1]
t = np.tanh(x)     # same shape as x, in [-1, 1]
pos = x > 0        # same shape as x, bool: strict, so 0 and -0.0 are "not positive"
```

**Step 3: the GELU pieces.**

```python
c = np.sqrt(2.0 / np.pi)                    # scalar
u = c * (x + 0.044715 * x ** 3)             # same shape as x
tu = np.tanh(u)                             # same shape as x
du = c * (1.0 + 3 * 0.044715 * x ** 2)      # same shape as x: du/dx
```

At `x = 1000`, `x ** 3` is `1e9`, which is fine for float64, and `np.tanh(u)` is exactly 1. Then `1 - tu²` is 0 and `d_gelu` is exactly 1, as the "extreme inputs" case expects.

Every scalar here (`c`, `0.5`, `alpha`) broadcasts against the array: NumPy treats a scalar as a 0-d array that stretches to any shape.

**Step 4: assemble the dict.** Each entry is a single expression from the plan table. Note `np.where(pos, 1.0, alpha)`: both value arguments are scalars, and `np.where` broadcasts them to `pos`'s shape.

## 8. Full solution

```python
# NumPy: every operation below is elementwise, so any input shape works unchanged
import numpy as np


# numerically stable logistic sigmoid
def _sigmoid(x):
    # e^{-|x|} is in (0, 1], so this exp can never overflow, even at x = +-1000
    e = np.exp(-np.abs(x))
    # x >= 0: 1/(1+e^{-x}); x < 0: e^{x}/(1+e^{x}); both branches are safe, so np.where is fine
    return np.where(x >= 0, 1.0 / (1.0 + e), e / (1.0 + e))


# x: float array of any shape; returns 10 arrays, each shaped like x
def activations(x: np.ndarray, alpha: float = 0.01) -> dict:
    # work in float64 so integer input can't change dtypes in np.where below
    x = np.asarray(x, dtype=float)
    # forward sigmoid, reused by its derivative s(1 - s)
    s = _sigmoid(x)
    # forward tanh, reused by its derivative 1 - t^2
    t = np.tanh(x)
    # strict mask: x = 0 counts as "not positive", giving relu'(0) = 0 and leaky'(0) = alpha
    pos = x > 0

    # GELU constant sqrt(2/pi)
    c = np.sqrt(2.0 / np.pi)
    # inner argument u(x) of the tanh approximation
    u = c * (x + 0.044715 * x ** 3)
    # tanh(u), shared by gelu and its derivative
    tu = np.tanh(u)
    # du/dx, needed for the chain rule through tanh(u)
    du = c * (1.0 + 3 * 0.044715 * x ** 2)

    # build the ten outputs from the shared pieces
    return {
        # forward sigmoid
        "sigmoid": s,
        # sigma' written in terms of the output, no second exp
        "d_sigmoid": s * (1.0 - s),
        # forward tanh
        "tanh": t,
        # tanh' = 1 - tanh^2, again from the output
        "d_tanh": 1.0 - t * t,
        # max(0, x) via the same strict mask
        "relu": np.where(pos, x, 0.0),
        # slope 1 where positive, 0 elsewhere (including exactly 0)
        "d_relu": pos.astype(float),
        # x on the positive side, alpha * x otherwise
        "leaky_relu": np.where(pos, x, alpha * x),
        # slope 1 where positive, alpha elsewhere (including exactly 0)
        "d_leaky_relu": np.where(pos, 1.0, alpha),
        # tanh-approximation GELU: 0.5 x (1 + tanh u)
        "gelu": 0.5 * x * (1.0 + tu),
        # product rule: 0.5(1 + t) + 0.5 x * dt/dx, with dt/dx = (1 - t^2) du/dx
        "d_gelu": 0.5 * (1.0 + tu) + 0.5 * x * (1.0 - tu * tu) * du,
    }
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `d_relu = [0, 0, 1]`, `d_leaky_relu = [0.01, 0.01, 1]`, `d_gelu = [-0.0861, 0.5, 1.0861]` | the `x = 0` convention and the full GELU derivative |
| Example 2 | `leaky_relu[1, 1] = -0.02` with `alpha = 0.2` | a 2-D input and a non-default `alpha` |
| exact zeros | `d_relu = [0, 0, 0, 1, 0]` | `0.0`, `-0.0` and `-1e-12` are not positive; `1e-12` is |
| extreme inputs | `sigmoid = [0, 0, 1, 1]`, `d_gelu = [0, 0, 1, 1]` | `±1000` stay finite: no `nan`, no `inf` |
| random 3d | arrays of shape `(2, 3, 4)` | nothing assumes 1-D |
| alpha zero | `d_leaky_relu` equals `d_relu` | `alpha = 0` makes Leaky ReLU into ReLU |
| gelu region | `d_gelu` peaks at `1.1277` (x = 1.5), dips to `-0.1277` (x = -1.5) | the product-rule term across the region where it's largest |
| scalar-like | `d_gelu = [0.9764]` at `x = 0.7` | a one-element array |

## 10. Complexity

For $n$ elements, each output is a constant number of elementwise passes: $O(n)$ time and $O(n)$ memory per output, ten outputs in all. The cost is dominated by the transcendental functions: one `exp` and two `tanh` calls per element.

In a real network the activation is never the bottleneck, the matrix multiplies are. But memory is: backprop has to keep something from the forward pass for every activation. That's why frameworks store the cheapest thing the derivative needs, the output $s$ for sigmoid, or only the 1-bit mask `x > 0` for ReLU. It's also why GELU is often recomputed in the backward pass instead of stored, and why fused kernels compute activation and derivative together.

## 11. If you got Wrong Answer

- **`d_relu` at `x = 0` is 1, and `d_leaky_relu` there is 1 instead of `alpha`.** Your mask is `x >= 0` (`wrong_relu_grad_at_zero.py`). Example 1 shows `d_relu = [0, 1, 1]` instead of `[0, 0, 1]`. It also fails "exact zeros" and "gelu region".
- **`d_gelu` is close but wrong, e.g. `0.977` instead of `1.0861` at `x = 2`.** You wrote `0.5 * (1 + tanh(u))` and dropped the `x * d/dx tanh(u)` term (`wrong_gelu_no_product_rule.py`).
- **`d_sigmoid` is negative or huge, e.g. at `x = 2` it gives `-2`.** You plugged `x` into `s(1 - s)` instead of `s` (`wrong_sigmoid_derivative.py`). It fails all eight cases.
- **`nan` in `sigmoid` at `±1000`.** You computed something like `np.exp(-x) / (1 + np.exp(-x))`, which is `inf / inf`. Use the two-branch form in section 4.
- **Overflow warnings but Accepted.** The naive `1 / (1 + np.exp(-x))` returns the right numbers, so the judge accepts it, but it still warns at `x = -1000`. Fix it anyway; the next formula you write that way won't be so lucky.

## 12. Follow-ups an interviewer might ask

- *Why did ReLU replace sigmoid in hidden layers?* $\sigma' \le 0.25$, so a chain of $L$ sigmoid layers scales gradients by at most $0.25^L$: vanishing gradients. ReLU's slope is exactly 1 on the active side. The weight scale still matters (problem 37, weight-initialization).
- *What's a dead ReLU, and how does Leaky ReLU help?* A unit whose pre-activation is negative for every input gets zero gradient forever. Leaky ReLU's slope `alpha` keeps a small gradient flowing.
- *Why do transformers use GELU or SwiGLU?* They are smooth near 0 and empirically train a little better. SwiGLU, a gated variant, is used in most current LLMs (problem 75, swiglu-ffn).
- *Exact GELU vs the tanh approximation?* Exact GELU is $x\,\Phi(x)$ with the normal CDF, via `erf`. The tanh form was cheaper on older hardware; PyTorch offers both via `approximate="tanh"`. They differ by less than about $10^{-3}$.
- *How do you plug these into backprop?* The backward pass multiplies the upstream gradient elementwise: `dx = dy * d_act(x)`. Problem 35 (dense-layer-forward-backward) does exactly that.
