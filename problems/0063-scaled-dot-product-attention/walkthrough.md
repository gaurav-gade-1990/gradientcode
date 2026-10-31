## 1. What the problem is really asking

Attention is a **soft dictionary lookup**. Each query asks "which keys look like me?", scores every key with a dot product, turns the scores into a probability distribution, and returns the matching weighted average of the values. A hard lookup would return one value; attention returns a blend, which is what makes it differentiable.

Strip the story and the problem is **one batched matrix product, a scale, a masked stable softmax, and a second batched matrix product**. The work is in the details that make the same four lines correct for every shape: no batch axes, one batch axis, or batch and head axes together; masks that broadcast from `(T_q, T_k)` or `(B, 1, 1, T_k)`; and scores as large as `1e4`.

The judge compares both `output` and `weights` at `rtol = 1e-6`, so a mistake that only shows in the weights (rows not summing to 1) is still caught.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `q` | `(..., T_q, d_k)` | one query vector per output position | left side of the score product |
| `k` | `(..., T_k, d_k)` | one key per position you can attend to | transposed on its last two axes |
| `v` | `(..., T_k, d_v)` | the content each key carries | averaged with the weights |
| `mask` | `None`, or bool broadcasting to `(..., T_q, T_k)` | `True` keeps a pair | dropped pairs get score `-inf` |

Easy to miss:

- **`d_k` is the last axis of `q` and `k`**, not of `v`. The case "d_k differs from d_v" has `d_k = 8`, `d_v = 2`.
- **`k.T` is wrong once there is a batch axis.** On a `(B, T, d)` array `.T` reverses *all* axes to `(d, T, B)`. Use `np.swapaxes(k, -1, -2)`.
- **The mask can be smaller than the scores.** A `(4, 4)` causal mask is applied to `(2, 3, 4, 4)` scores, and a `(2, 1, 1, 5)` padding mask to `(2, 2, 3, 5)` scores. Broadcasting handles both if you never reshape it yourself.

## 3. The math

For one batch element, with $Q \in \mathbb{R}^{T_q \times d_k}$, $K \in \mathbb{R}^{T_k \times d_k}$, $V \in \mathbb{R}^{T_k \times d_v}$:

$$
S = \frac{Q K^\top}{\sqrt{d_k}} \in \mathbb{R}^{T_q \times T_k}, \qquad
W_{ij} = \frac{e^{S_{ij}} \,[\text{mask}_{ij}]}{\sum_{l} e^{S_{il}} \,[\text{mask}_{il}]}, \qquad
O = W V \in \mathbb{R}^{T_q \times d_v}.
$$

$[\text{mask}_{ij}]$ is 1 for a kept pair and 0 for a dropped one. Setting $S_{ij} = -\infty$ does exactly that, because $e^{-\infty} = 0$, and the denominator then sums only over kept keys.

**Why divide by $\sqrt{d_k}$.** Suppose the entries of $q$ and $k$ are independent with mean 0 and variance 1. Then $q \cdot k = \sum_{m=1}^{d_k} q_m k_m$ is a sum of $d_k$ independent terms, each with mean 0 and variance $\mathbb{E}[q_m^2]\,\mathbb{E}[k_m^2] = 1$. So

$$
\operatorname{Var}(q \cdot k) = d_k, \qquad \operatorname{Var}\!\left(\frac{q \cdot k}{\sqrt{d_k}}\right) = 1 .
$$

Without the scale, scores grow like $\sqrt{d_k}$ and the softmax drifts toward one-hot. That kills learning. Differentiate the softmax $w = \operatorname{softmax}(s)$:

$$
\frac{\partial w_i}{\partial s_j} = w_i(\delta_{ij} - w_j).
$$

If one weight is near 1 and the rest near 0, every entry is near 0: $w_i(1 - w_i) \approx 0$ on the diagonal and $w_i w_j \approx 0$ off it. The scores stop receiving gradient.

**Why subtracting the row max is allowed.** For any constant $c$,

$$
\frac{e^{s_j - c}}{\sum_l e^{s_l - c}} = \frac{e^{-c}\, e^{s_j}}{e^{-c} \sum_l e^{s_l}} = \frac{e^{s_j}}{\sum_l e^{s_l}} .
$$

Pick $c = \max_l s_l$ over the kept keys. Every exponent is then $\le 0$, so nothing overflows, and the largest term is $e^0 = 1$, so the denominator is at least 1. Because every row keeps at least one key, the max is finite and $-\infty - c$ stays $-\infty$, never `nan`.

## 4. Trace Example 2 by hand

`q` is `(2, 2)`, `k` is `(2, 2)` (the identity), `v = [[10], [20]]` is `(2, 1)`, and the mask drops query 0's view of key 1.

| step | shape | query 0 | query 1 |
|---|---|---|---|
| `q @ k^T` | `(2, 2)` | `[1, 1]` | `[0, 2]` |
| `/ sqrt(2)` | `(2, 2)` | `[0.7071, 0.7071]` | `[0, 1.4142]` |
| masked | `(2, 2)` | `[0.7071, -inf]` | `[0, 1.4142]` |
| minus row max | `(2, 2)` | `[0, -inf]` | `[-1.4142, 0]` |
| weights | `(2, 2)` | `[1, 0]` | `[0.1956, 0.8044]` |
| `weights @ v` | `(2, 1)` | `10` | `18.0443` |

Query 0 scores both keys equally, so without the mask its weights would be `[0.5, 0.5]`. The mask forces all the weight onto key 0, so the output is exactly `v[0] = 10`. If you mask *after* the softmax by multiplying, you keep `[0.5, 0]`, the row sums to `0.5`, and the output is `5`.

**Example 1** is the unmasked version: scores `[0.7071, 0]`, weights `[0.6698, 0.3302]`, output `0.6698 * [1, 2] + 0.3302 * [3, 4] = [1.6605, 2.6605]`.

**The hidden case "huge scores"** has `q` scaled by 100 and `k` by 30. Its scaled scores reach `7569` in magnitude (row 0 runs from `-3976` to `6076`). $e^{6076}$ is `inf` in float64, and `inf / inf` is `nan`. After the max shift, the row max becomes `0` and every other entry is thousands below it, so the weights are one-hot (the largest off-peak weight in any row is `2.9e-34`) and each output row is a copy of one value row: row 0 of the output equals `v[2]`.

## 5. Key idea: let broadcasting do the batching

`@` treats every axis except the last two as a batch axis and broadcasts them. `np.swapaxes(k, -1, -2)` turns `(..., T_k, d_k)` into `(..., d_k, T_k)` without touching the leading axes. `np.where(mask, scores, -np.inf)` broadcasts the mask against the scores by aligning trailing axes:

| mask | scores | how it lines up |
|---|---|---|
| `(4, 4)` causal | `(2, 3, 4, 4)` | treated as `(1, 1, 4, 4)`: same mask for every batch and head |
| `(2, 1, 1, 5)` padding | `(2, 2, 3, 5)` | per batch, repeated over heads and queries |
| `(6, 7)` all-true | `(2, 6, 7)` | treated as `(1, 6, 7)` |

Reductions use `axis=-1, keepdims=True`, so the row max and row sum have shape `(..., T_q, 1)` and broadcast back across the key axis. Written this way, no line of the solution mentions a batch size.

## 6. Plan before you code

```
d_k = q.shape[-1]
scores = q @ swap_last_two(k) / sqrt(d_k)       # (..., T_q, T_k)
if mask: scores = where(mask, scores, -inf)      # broadcast mask
scores -= max over last axis (keepdims)          # (..., T_q, 1) broadcast
e = exp(scores)
weights = e / sum over last axis (keepdims)      # rows sum to 1
return weights @ v, weights                      # (..., T_q, d_v), (..., T_q, T_k)
```

## 7. Build it one piece at a time

**Step 1: the scaled scores.**

```python
d_k = q.shape[-1]
scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d_k)   # (..., T_q, d_k)@(..., d_k, T_k) -> (..., T_q, T_k)
```

**Step 2: the mask.** `-np.inf` rather than a large negative number like `-1e9`. Both pass the tests here, but `-1e9` only works while every real score stays far above it, while `-inf` makes the zero exact whatever the scores are.

```python
if mask is not None:
    scores = np.where(mask, scores, -np.inf)          # mask broadcasts to (..., T_q, T_k)
```

**Step 3: the stable softmax over keys.**

```python
scores = scores - np.max(scores, axis=-1, keepdims=True)   # row max (..., T_q, 1); kept entries now <= 0
e = np.exp(scores)                                          # exp(-inf) = 0 exactly
weights = e / np.sum(e, axis=-1, keepdims=True)             # denominator >= 1, so no divide by 0
```

**Step 4: the weighted average.**

```python
return weights @ v, weights    # (..., T_q, T_k)@(..., T_k, d_v) -> (..., T_q, d_v)
```

## 8. Full solution

```python
# arrays in, arrays out
import numpy as np


# softmax(q k^T / sqrt(d_k) + mask) v, for any number of leading batch/head axes
def attention(q, k, v, mask=None):
    d_k = q.shape[-1]  # the dot-product length sets the scale, not v's width
    # (..., T_q, T_k); swapaxes transposes only the last two axes, so batch axes are untouched
    scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d_k)
    # a mask was given: dropped pairs must end with weight exactly 0
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)  # mask broadcasts; exp(-inf) is 0 after the softmax
    # shift each row so its max is 0; softmax is unchanged and exp can no longer overflow
    scores = scores - np.max(scores, axis=-1, keepdims=True)
    e = np.exp(scores)  # every kept entry is in (0, 1], masked ones are exactly 0
    weights = e / np.sum(e, axis=-1, keepdims=True)  # (..., T_q, T_k), each row sums to 1
    return weights @ v, weights  # (..., T_q, d_v) output and the probabilities the judge checks
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | output `[[1.6605, 2.6605]]`, weights `[[0.6698, 0.3302]]` | the basic formula with the `sqrt(2)` scale |
| Example 2 | output `[[10], [18.0443]]` | a mask applied before the softmax |
| Example 3 | output `[[[0.3302]], [[0.6698]]]` | one leading batch axis, `(2, 1, 2)` |
| d_k differs from d_v | `(3, 2)`, weights row 0 `[0.7543, 0.0444, ...]` | scale by `d_k = 8`, not `d_v = 2` |
| causal mask 2d | weights row 0 `[1, 0, 0, 0]` | a lower-triangular mask |
| batched heads with broadcast causal mask | `(2, 3, 4, 6)` | a `(4, 4)` mask over `(2, 3, 4, 4)` scores |
| padding mask broadcast over heads and queries | `(2, 2, 3, 3)` | a `(2, 1, 1, 5)` mask: different per batch, same per head |
| huge scores | one-hot weights, output `[0, 0] = 0.139` | scores up to `7569` need the max shift |
| single key | every weight `1` | `T_k = 1`, so the output repeats `v[0]` |
| explicit all-true mask | `(2, 6, 5)` | a mask that drops nothing must match no mask |

## 10. Complexity

Per batch element, the two products cost $O(T_q T_k d_k)$ and $O(T_q T_k d_v)$, so time is $O(T_q T_k (d_k + d_v))$. Memory is $O(T_q T_k)$ for the score matrix. That quadratic term is the problem at scale: at $T = 32{,}000$ one head's float32 score matrix is about 4 GB. FlashAttention never materializes it, computing the softmax in tiles with a running max (problem 77). During generation, $T_q = 1$ per step and the cost is linear in the cached length (problem 69).

## 11. If you got Wrong Answer

- **Example 2 gives `5` instead of `10`, and masked rows don't sum to 1.** You masked after the softmax by multiplying weights by the mask. Mask the scores with `-inf` first. Filling with `0` instead of `-inf` is also wrong: it fails the same four masked cases, because a score of 0 still gets weight.
- **Example 1 gives `1.5379` instead of `1.6605`.** You didn't divide by `sqrt(d_k)`. Only "huge scores" and "single key" survive, because their weights are one-hot or trivially `1` either way.
- **Example 1 passes but Example 2 gives `18.808` instead of `18.0443`.** You scaled by `sqrt(v.shape[-1])`. Example 1 has `d_k = d_v = 2`, so it can't tell.
- **Only "huge scores" fails, with `nan`.** You skipped the max shift.
- **Runtime Error on the batched-heads cases, Wrong Answer on Example 3.** You used `k.T`, which reverses all axes.

## 12. Follow-ups an interviewer might ask

- *How do you build a causal mask, and how does it combine with padding?* `np.tril(np.ones((T, T), bool))`, combined with a padding mask by `&` after broadcasting (problem 64).
- *What if a row has every key masked?* The max is `-inf`, `-inf - (-inf)` is `nan`, and the row is poisoned. Real code either guarantees one kept key, as this problem does, or replaces fully masked rows with zeros after the softmax.
- *How does multi-head attention use this?* Project to `(B, h, T, d_k)` and call this function once; the head axis is just another leading axis (problem 65).
- *How do you avoid the `(T_q, T_k)` matrix?* Process keys in blocks and keep a running max and running sum per row, rescaling as the max grows (problem 77, online softmax).
