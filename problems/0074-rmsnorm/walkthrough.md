## 1. What the problem is really asking

Every transformer block normalizes its sublayer inputs so that activations stay at a predictable scale no matter how the residual stream grows (problem 68). LayerNorm does two things for that: it subtracts the mean and divides by the standard deviation. RMSNorm, used by LLaMA, Mistral and most recent LLMs, keeps only the second. It divides each vector by its root mean square and multiplies by a learned per-feature weight.

Strip the story and the problem is **one reduction over the last axis, one square root, and two broadcasts**. Three details decide correctness: reduce per row, not over the whole array; don't subtract the mean; and put `eps` inside the square root. The judge compares the output, same shape as `x`, at `rtol = 1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(d,)`, `(N, d)` or `(B, T, d)` | the vectors to normalize, one per row | RMS over the last axis |
| `weight` | `(d,)` | the learned gain $w$ | multiplies every row elementwise |
| `eps` | scalar, default `1e-6` | keeps the denominator away from 0 | added to the mean square before `sqrt` |

Easy to miss:

- **Only the last axis is reduced.** A `(2, 3, 16)` input has six RMS values, one per vector, shape `(2, 3, 1)`.
- **No centering and no bias.** "rows with offsets" adds `+5`, `-3`, `0` and `+10` to whole rows; RMSNorm must keep that offset in the output, not remove it.
- **`eps` placement is observable.** `sqrt(ms + eps)` and `sqrt(ms) + eps` differ most when `ms` is small, which "tiny values eps matters" and "all zeros row" exploit.

## 3. The math

For one vector $x \in \mathbb{R}^d$,

$$
r = \sqrt{\frac{1}{d}\sum_{j=1}^{d} x_j^2 + \epsilon}, \qquad y_i = \frac{x_i}{r}\, w_i .
$$

**What it normalizes.** Ignoring $\epsilon$, the output before the gain has

$$
\frac{1}{d}\sum_i \left(\frac{x_i}{r}\right)^2 = \frac{\frac{1}{d}\sum_i x_i^2}{r^2} = 1,
$$

so every row is rescaled to unit mean square, i.e. its Euclidean norm becomes $\sqrt{d}$. The direction of $x$ is untouched: RMSNorm is a projection onto a sphere of radius $\sqrt d$, followed by a per-feature stretch $w$.

**Relation to LayerNorm.** LayerNorm computes $(x - \mu)/\sqrt{\sigma^2 + \epsilon}$ with $\sigma^2 = \frac1d\sum (x_j - \mu)^2$. When the mean $\mu$ is 0, $\sigma^2$ equals the mean square and the two coincide. RMSNorm bets that re-centering isn't needed and saves one reduction.

**Scale invariance and the gradient.** For any $\alpha > 0$ and $\epsilon = 0$, $\operatorname{RMSNorm}(\alpha x) = \operatorname{RMSNorm}(x)$, so the layer doesn't care how large its input is. Differentiating shows what this means for backprop. With $m = \frac1d\sum_j x_j^2$ and $r = \sqrt{m + \epsilon}$,

$$
\frac{\partial r}{\partial x_j} = \frac{1}{2r}\cdot\frac{2x_j}{d} = \frac{x_j}{d\,r}, \qquad
\frac{\partial y_i}{\partial x_j} = w_i\left(\frac{\delta_{ij}}{r} - \frac{x_i}{r^2}\frac{\partial r}{\partial x_j}\right) = w_i\left(\frac{\delta_{ij}}{r} - \frac{x_i x_j}{d\,r^3}\right).
$$

For $\epsilon = 0$, multiplying the Jacobian by $x$ gives $w_i(x_i/r - x_i\, m/r^3) = 0$: moving along $x$ itself doesn't change the output, which is scale invariance again. A finite-difference check of this Jacobian on `x = [1, 2, 3]` agrees to `1.8e-10`.

**Numerics.** $\epsilon$ is what keeps an all-zero row finite: with $x = 0$, $r = \sqrt{\epsilon}$ and $y = 0/\sqrt\epsilon = 0$ instead of `0 / 0 = nan`. Where $\epsilon$ goes changes the answer: "tiny values eps matters" has entries around `1e-3`, so the mean square is about `1e-6`, the same size as $\epsilon$, and the correct first output is `0.2197` while `sqrt(ms) + eps` gives `0.4841`. Squaring can also overflow in low precision: `300 * 300` is `inf` in float16, which is why real implementations upcast to float32 for the reduction.

## 4. Trace Example 2 by hand

`x = [[1, 2, 3], [-2, 0, 2]]` is `(2, 3)`, `weight = [1, 0.5, 2]`, `eps = 1e-6`.

| quantity | shape | row 0 | row 1 |
|---|---|---|---|
| `x * x` | `(2, 3)` | `[1, 4, 9]` | `[4, 0, 4]` |
| mean over last axis | `(2, 1)` | `4.6667` | `2.6667` |
| `rms = sqrt(ms + eps)` | `(2, 1)` | `2.1602` | `1.633` |
| `x / rms` | `(2, 3)` | `[0.4629, 0.9258, 1.3887]` | `[-1.2247, 0, 1.2247]` |
| `* weight` | `(2, 3)` | `[0.4629, 0.4629, 2.7775]` | `[-1.2247, 0, 2.4495]` |

Two broadcasts happen. `x / rms` is `(2, 3) / (2, 1)`: the size-1 axis stretches so each row is divided by its own RMS. `* weight` is `(2, 3) * (3,)`: `weight` is treated as `(1, 3)` and every row is scaled by the same gains. Row 1 has mean 0, so LayerNorm would give the same normalized values there; row 0 has mean 2, and subtracting it would give `-1.2247` for the first entry instead of `0.4629`.

**Example 1** is a single 1-D vector `[3, 4]` with `eps = 1e-4`: mean square `12.5`, `rms = sqrt(12.5001) = 3.5355`, output `[0.8485, 1.1314]`. With one row, a global RMS over the whole array happens to be right, which is why only the multi-row cases catch that bug.

**"all zeros row"**: row 0 is all zeros, so the output row is exactly `[0, 0, 0, 0]`. Row 1 is `[1, -1, 1, -1]` with mean square 1, so the output is the weight times the signs, `[1, -2, 3, -4]` (to within `eps`: `0.999995` before the weight).

## 5. Key idea: `keepdims=True` makes the broadcast line up

`np.mean(x * x, axis=-1)` on a `(2, 3)` array returns shape `(2,)`. Dividing `(2, 3)` by `(2,)` aligns trailing axes, so NumPy tries to match the `2` against the `3` and raises an error. For a `(3, 3)` input it would silently divide each *column* by a row's RMS. `keepdims=True` returns `(2, 1)`, which aligns with rows. The same habit fixes every row-wise reduction you'll write (softmax, LayerNorm, attention).

## 6. Plan before you code

```
ms  = mean(x * x over the last axis, keepdims)     # (..., 1)
rms = sqrt(ms + eps)                               # (..., 1), eps inside
return x / rms * weight                            # (..., d), a new array
```

| variant | formula | what it gets wrong |
|---|---|---|
| correct | `x / sqrt(mean(x², -1) + eps) * w` | |
| LayerNorm-like | subtract the row mean first | removes offsets |
| eps outside | `x / (sqrt(mean(x², -1)) + eps) * w` | small and zero rows |
| global | `mean(x²)` with no axis | rows of different scales |

## 7. Build it one piece at a time

**Step 1: the per-row mean square.** `x * x` is elementwise and allocates a new array, so `x` is never modified.

```python
ms = np.mean(x * x, axis=-1, keepdims=True)     # (..., d) -> (..., 1)
```

**Step 2: the RMS with `eps` inside.**

```python
rms = np.sqrt(ms + eps)                          # (..., 1); never 0 because eps > 0
```

**Step 3: normalize and scale.**

```python
return x / rms * weight                          # (..., d)/(..., 1) then *(d,)
```

`x / rms` creates a new array, so the "don't modify `x` in place" rule is satisfied. Writing `x /= rms` would overwrite the caller's array.

## 8. Full solution

```python
# arrays in, arrays out
import numpy as np


# scale each last-axis vector to unit mean square, then apply the per-feature gain
def rmsnorm(x: np.ndarray, weight: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    # (..., 1): one RMS per vector; keepdims so it broadcasts back over d; eps inside the sqrt
    rms = np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + eps)
    return x / rms * weight  # (..., d); no mean subtracted, no bias, and a new array, so x is untouched
```

## 9. How the test cases map to the code

| test case | expected (first values) | what it checks |
|---|---|---|
| Example 1 | `[0.8485, 1.1314]` | a 1-D input with `eps = 1e-4` |
| Example 2 | `[[0.4629, 0.4629, 2.7775], [-1.2247, 0, 2.4495]]` | per-row RMS and the weight broadcast |
| all zeros row | `[[0, 0, 0, 0], [1, -2, 3, -4]]` | `eps` keeps a zero row finite |
| tiny values eps matters | `0.2197` | entries near `1e-3`: `eps` inside the square root |
| rows with offsets | `-0.0496` | rows shifted by `+5`, `-3`, `+10`: no mean subtraction |
| rows with different scales | `-1.8536` | rows at scales `0.1`, `1`, `50`: per-row, not global |
| 3d batch | `(2, 3, 16)`, `0.1074` | reduction over the last axis of a 3-D array |
| d = 1 | `[[3], [-3]]` | a single feature normalizes to its sign times the weight |

## 10. Complexity

$O(n)$ time for $n$ elements of `x`: one pass to square and average, one to divide and scale. Memory is $O(n)$ for the output and $O(n/d)$ for the RMS values. RMSNorm is memory-bound in practice: it reads and writes every activation once and does almost no arithmetic, so on a GPU it is fused into the neighbouring matmul or run as one kernel per row. Compared to LayerNorm it drops one reduction (the mean) and the bias, which is a small but real saving repeated twice per layer per token.

## 11. If you got Wrong Answer

- **Example 1 gives `-0.9998` instead of `0.8485`.** You subtracted the mean, which is LayerNorm. Only "all zeros row", whose rows already have mean 0, passes.
- **Example 1 passes, Example 2 gives `0.5222` instead of `0.4629`.** You took one RMS over the whole array (`np.mean(x * x)` with no axis). Example 1 has one row, so it can't tell.
- **"tiny values eps matters" gives `0.4841` instead of `0.2197`, and Example 1 is off in the fifth digit (`0.848504`).** `eps` is outside the square root.
- **A broadcasting error, or wrong values on square inputs.** You dropped `keepdims=True`.

## 12. Follow-ups an interviewer might ask

- *Why did LLMs switch from LayerNorm to RMSNorm?* It trains about as well, is cheaper (one reduction, no bias), and the re-centering turned out not to matter for stability. Scale invariance is what does the work.
- *Where is it placed in a LLaMA block?* Pre-norm: `h = x + attn(rmsnorm(x))`, `out = h + swiglu(rmsnorm(h))`, plus a final RMSNorm before the output head (problems 68 and 75).
- *What is the backward pass?* From section 3, with $\hat x = x/r$ and $g = w \odot \partial L/\partial y$: $\partial L/\partial x = \frac{1}{r}\big(g - \hat x \cdot \frac{1}{d}\sum_j g_j \hat x_j\big)$, and $\partial L/\partial w = \sum_{\text{rows}} \hat x \odot \partial L/\partial y$.
- *Why compute it in float32 when the model runs in bf16?* Squaring large activations can overflow, and summing many small squares loses precision in a 7-bit mantissa. Upcast for the reduction, then cast the result back.
