## 1. What the problem is really asking

Every transformer block has an MLP after attention: attention moves information between tokens, and the MLP transforms each token on its own. The original MLP is `act(x W1) W2`, one up-projection, a nonlinearity, one down-projection. SwiGLU, used by LLaMA, PaLM and most recent LLMs, adds a second up-projection and lets one branch **gate** the other elementwise. The gate goes through SiLU; the value doesn't.

Strip the story and the problem is **three matrix products and one elementwise product**, with SiLU on exactly one branch. The only ways to get it wrong are to activate the wrong branch, use the wrong activation, or activate in the wrong place. The judge compares the `(..., d)` output at `rtol = 1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(d,)`, `(N, d)` or `(B, T, d)` | token vectors | the input to both up-projections |
| `W1` | `(d, h)` | the gate projection | `silu(x @ W1)` |
| `W3` | `(d, h)` | the value projection | `x @ W3`, not activated |
| `W2` | `(h, d)` | the down-projection | applied to the gated product |

Easy to miss:

- **SiLU goes on `x @ W1` only.** `W1` and `W3` have the same shape, so swapping them raises no error, just wrong numbers.
- **SiLU is `z * sigmoid(z)`, not `sigmoid(z)`.** The plain sigmoid gate is the original GLU, a different function.
- **The activation comes before the product.** `SiLU(a) * b` is not `SiLU(a * b)`.
- **There are no biases.**

## 3. The math

With $a = xW_1$ (the gate pre-activation) and $b = xW_3$ (the value), both of shape $(\dots, h)$,

$$
\operatorname{FFN}(x) = \big(\operatorname{SiLU}(a) \odot b\big) W_2, \qquad \operatorname{SiLU}(z) = z\,\sigma(z) = \frac{z}{1 + e^{-z}} .
$$

Shapes: $(\dots, d)(d, h) \to (\dots, h)$ for both branches, the product stays $(\dots, h)$, and $(\dots, h)(h, d) \to (\dots, d)$.

**What SiLU looks like.** For large positive $z$, $\sigma(z) \to 1$ and $\operatorname{SiLU}(z) \to z$, like ReLU. For large negative $z$, $\sigma(z) \to 0$ faster than $z$ grows, so $\operatorname{SiLU}(z) \to 0$. In between it dips below zero: on a scratch grid over $[-10, 10]$ the minimum is `-0.2785` at $z \approx -1.278$. Unlike ReLU it is smooth everywhere.

**Its derivative.** By the product rule, using $\sigma'(z) = \sigma(z)(1 - \sigma(z))$,

$$
\operatorname{SiLU}'(z) = \sigma(z) + z\,\sigma(z)(1 - \sigma(z)) = \sigma(z)\big(1 + z(1 - \sigma(z))\big).
$$

At $z = 0$ it is $\tfrac12$, it approaches 1 for large positive $z$ and 0 for large negative $z$, and it is never exactly zero on a whole half-line, so there are no "dead" units as with ReLU.

**Why gating helps: the gradients of the two branches.** Let $u = \operatorname{SiLU}(a) \odot b$ and $g = \partial L / \partial u$. Then

$$
\frac{\partial L}{\partial b} = g \odot \operatorname{SiLU}(a), \qquad \frac{\partial L}{\partial a} = g \odot b \odot \operatorname{SiLU}'(a).
$$

Each branch's gradient is scaled by the other branch's value. The output is a product of two linear functions of $x$, passed through a smooth gate, so the unit can express multiplicative interactions that a single activation can't. Empirically (Shazeer, 2020) this gives lower perplexity at the same parameter count.

**Parameter budget.** A standard MLP with hidden size $4d$ has $2 \cdot d \cdot 4d = 8d^2$ weights. SwiGLU has three matrices, $3dh$ weights, so matching the budget needs $h = \tfrac{2}{3} \cdot 4d$. For LLaMA-7B, $d = 4096$ gives $10{,}922.7$, rounded up to a hardware-friendly `11008`.

**Numerics.** The constraint keeps $|a| \le 50$, so $e^{-a} \le e^{50} \approx 5 \times 10^{21}$, finite in float64. The form `z / (1 + exp(-z))` is also safe further out in the sense that matters: at $z = -1000$, `exp(1000)` overflows to `inf` with a warning, and `-1000 / inf` is `-0.0`, the correct limit. "large negative gate" has gate pre-activations `[-40, 40]`, giving SiLU values `[-0, 40]` (the first is about $-1.7 \times 10^{-16}$).

## 4. Trace Example 2 by hand

`x = [[0.5, 1], [2, 0]]` is `(2, 2)`, `h = 3`, so `W1` and `W3` are `(2, 3)` and `W2` is `(3, 2)`.

| quantity | shape | row 0 | row 1 |
|---|---|---|---|
| gate `a = x @ W1` | `(2, 3)` | `[0.5, 1, 0.5]` | `[2, 0, -2]` |
| `SiLU(a)` | `(2, 3)` | `[0.3112, 0.7311, 0.3112]` | `[1.7616, 0, -0.2384]` |
| value `b = x @ W3` | `(2, 3)` | `[0.5, 1.5, 2]` | `[2, 2, 0]` |
| `SiLU(a) * b` | `(2, 3)` | `[0.1556, 1.0966, 0.6225]` | `[3.5232, 0, 0]` |
| `@ W2` | `(2, 2)` | `[0.7781, 1.719]` | `[3.5232, 0]` |

`W2`'s third row is `[1, 1]`, so hidden unit 2 feeds both outputs: row 0's output is `[0.1556 + 0.6225, 1.0966 + 0.6225]`. In row 1, unit 1's gate pre-activation is `0`, and `SiLU(0) = 0` shuts that unit off even though its value is `2`. Unit 2 has a value of `0`, so its negative gate `-0.2384` contributes nothing either. Each unit is open only when both branches are nonzero.

**Example 1** is the simplest check of the branch roles: `x = [1, -1]`, `W1 = I`, `W3 = diag(2, 3)`, `W2 = I`. The gate is `SiLU([1, -1]) = [0.7311, -0.2689]`, the value is `[2, -3]`, and the output is `[1.4621, 0.8068]`. A sigmoid gate gives `-0.8068` for the second entry, because $\sigma(-1) = 0.2689$ is positive while $\operatorname{SiLU}(-1)$ is negative.

## 5. Key idea: `@` handles every leading shape

`x @ W1` treats every axis of `x` except the last as a batch axis. A `(d,)` vector gives `(h,)`, a `(5, 8)` batch gives `(5, 16)`, and a `(2, 3, 4)` input gives `(2, 3, 6)`. The elementwise product needs the two branches to have the same shape, which they always do since `W1` and `W3` share a shape. So one line works for all three input ranks with no reshaping, and nothing in the code mentions the batch size.

## 6. Plan before you code

```
gate  = silu(x @ W1)        # (..., h)
value = x @ W3              # (..., h)
return (gate * value) @ W2  # (..., d)
```

| variant | hidden activation | correct? |
|---|---|---|
| SwiGLU | `SiLU(xW1) * xW3` | yes |
| GLU | `sigmoid(xW1) * xW3` | no |
| swapped branches | `xW1 * SiLU(xW3)` | no |
| activation after product | `SiLU(xW1 * xW3)` | no |

## 7. Build it one piece at a time

**Step 1: SiLU.**

```python
def silu(z):
    return z / (1.0 + np.exp(-z))       # same as z * sigmoid(z), one division
```

**Step 2: the two up-projections.**

```python
gate = silu(x @ W1)                      # (..., d)@(d, h) -> (..., h), activated
value = x @ W3                           # (..., h), linear
```

**Step 3: gate and project down.**

```python
return (gate * value) @ W2               # (..., h) * (..., h) -> (..., h); @ (h, d) -> (..., d)
```

In Python `*` and `@` have the same precedence and group left to right, so `gate * value @ W2` would also work, but the parentheses make the order obvious to a reader. Writing `gate * (value @ W2)` is the bug to avoid: it fails with a shape error when `h != d`.

## 8. Full solution

```python
# arrays in, arrays out
import numpy as np


# SiLU (Swish): z * sigmoid(z), written as one division
def silu(z):
    return z / (1.0 + np.exp(-z))  # |z| <= 50 here, so exp stays finite; -> z for large z, -> 0 for very negative z


# LLaMA-style gated MLP: SiLU on the gate branch, linear value branch, then down-project
def swiglu_ffn(x: np.ndarray, W1: np.ndarray, W3: np.ndarray, W2: np.ndarray) -> np.ndarray:
    gate = silu(x @ W1)  # (..., h): the only activated branch
    value = x @ W3  # (..., h): not activated
    return (gate * value) @ W2  # gate the value elementwise, then (..., h) @ (h, d) -> (..., d)
```

## 9. How the test cases map to the code

| test case | expected (first values) | what it checks |
|---|---|---|
| Example 1 | `[1.4621, 0.8068]` | SiLU, not sigmoid, on the gate; a 1-D input |
| Example 2 | `[[0.7781, 1.719], [3.5232, 0]]` | the branch roles and the down-projection |
| batch of tokens | `(5, 8)`, `4.4575` | a 2-D batch with `h = 16` |
| 3d input | `(2, 3, 4)`, `-24.7023` | a 3-D input through `@` |
| large negative gate | `[[0, 400]]` | gate pre-activations `±40`: SiLU shuts off one unit, passes the other |
| h = 1 | `(3, 4)`, `-0.4019` | a single hidden unit |
| zero input | all zeros | no biases, so zero in gives zero out |

## 10. Complexity

Three matrix products cost $O(N d h)$ for $N$ tokens; the SiLU and the elementwise product are $O(Nh)$. Memory is $O(Nh)$ for the two hidden activations. In a real LLM the MLP holds about two-thirds of each block's parameters and most of its FLOPs at short context. Inference kernels fuse `W1` and `W3` into one `(d, 2h)` matrix so both branches come from a single matmul, then split the result in half.

## 11. If you got Wrong Answer

- **Example 1's second entry is `-0.8068` instead of `0.8068`.** You used a plain sigmoid gate (GLU). Multiply by `z`. "large negative gate" gives `10` instead of `400`.
- **Example 1 gives `1.7616` for the first entry.** You put SiLU on the value branch, or applied SiLU after the product. Both give `1.7616` here; Example 2 tells them apart (`1.0364` for the swapped branches, `0.8716` for SiLU after the product).
- **A shape error such as `(5,16)` against `(5,8)`.** You projected one branch down before the product, for example `gate * (value @ W2)`. Multiply in the hidden space first.

## 12. Follow-ups an interviewer might ask

- *What are GEGLU and ReGLU?* The same structure with GELU or ReLU as the gate's activation. Shazeer's paper compared them; SwiGLU and GEGLU did best.
- *Why shrink the hidden size to $\tfrac{2}{3} \cdot 4d$?* To keep the parameter count of a standard $4d$ MLP with three matrices instead of two (section 3).
- *How does a mixture-of-experts layer use this?* Each expert is a SwiGLU block, and a router sends each token to its top-k experts and mixes their outputs (problem 80).
- *Where does it sit in a LLaMA block?* `out = h + swiglu_ffn(rmsnorm(h))`, the second residual sublayer after attention (problems 68 and 74).
