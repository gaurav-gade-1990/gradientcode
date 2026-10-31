## 1. What the problem is really asking

Layer normalization is batch normalization turned sideways. Instead of normalizing each feature across the batch, it normalizes **each example across its own features**: one mean and one variance per row (per token, in a transformer). Nothing depends on the other examples in the batch, so there are no running statistics and no train/eval difference. That's why every transformer uses it (or its cousin RMSNorm).

This problem asks for the forward pass and the full backward pass in one function. Under the story:

- **Forward:** standardize along the last axis, then `gamma * x_hat + beta`.
- **Backward:** the same three-path gradient as batch norm (problem 40), with the means taken over the **last** axis; and parameter gradients that sum over **every leading** axis.

The judge compares `(out, dx, dgamma, dbeta)` with `rtol=1e-6`, for inputs of shape `(D,)`, `(N, D)` and `(B, T, D)`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(..., D)`, 1 to 3 dims | activations; each last-axis vector is one example | statistics over axis `-1` |
| `gamma`, `beta` | `(D,)` | learned per-feature scale and shift | broadcast over leading axes |
| `dout` | same as `x` | upstream gradient | |
| `eps` | float, default `1e-5` | stability constant | inside the square root |
| return | `x.shape`, `x.shape`, `(D,)`, `(D,)` | `out, dx, dgamma, dbeta` | |

The details that are easy to miss:

- **Two different reduction directions.** Statistics (and the means inside `dx`) reduce over the **last** axis. Parameter gradients reduce over **all the other** axes, because `gamma[j]` is used by every row.
- **For `(B, T, D)` there are two leading axes.** `dgamma` must sum over both `B` and `T`. Summing over axis 0 only leaves a `(T, D)` array.
- **For 1-D `x` there are no leading axes**, so `dgamma = dout * x_hat` with nothing summed. The code has to handle that without a special case.

## 3. The math

Take one row $x \in \mathbb{R}^D$:

$$\mu = \frac1D \sum_{k=1}^{D} x_k, \qquad \sigma^2 = \frac1D \sum_{k=1}^{D} (x_k - \mu)^2, \qquad s = \frac{1}{\sqrt{\sigma^2 + \epsilon}}, \qquad \hat x_k = (x_k - \mu)\, s,$$

$$\text{out}_k = \gamma_k \hat x_k + \beta_k.$$

Note that $\gamma$ and $\beta$ are indexed by the **feature** $k$, not shared within the row. That's the opposite of batch norm, where the parameters are per feature and the statistics are too.

**Parameter gradients.** Over all rows $r$ (all leading positions):

$$d\beta_k = \sum_r dout_{rk}, \qquad d\gamma_k = \sum_r dout_{rk}\, \hat x_{rk}.$$

**Input gradient.** Let $g_k = \partial L / \partial \hat x_k = \gamma_k\, dout_k$. Every $x_i$ in the row moves $\mu$ and $\sigma^2$, and through them every $\hat x_k$. The derivative is the same as in batch norm with $M$ replaced by $D$:

- $\partial \mu / \partial x_i = 1/D$;
- $\partial \sigma^2 / \partial x_i = \frac2D (x_i - \mu)$ (the term through $\mu$ vanishes because deviations sum to 0);
- $\partial s / \partial x_i = -\tfrac12 s^3 \cdot \frac2D (x_i - \mu) = -\frac{s^2}{D}\hat x_i$.

So

$$\frac{\partial \hat x_k}{\partial x_i} = s\Big([k = i] - \frac1D - \frac{\hat x_k\, \hat x_i}{D}\Big),$$

and summing against $g_k$:

$$\boxed{dx_i = s\Big(g_i - \overline{g} - \hat x_i\, \overline{g \hat x}\Big)}, \qquad \overline{g} = \frac1D\sum_k g_k, \quad \overline{g\hat x} = \frac1D \sum_k g_k \hat x_k.$$

The three terms are the direct path, the path through the mean, and the path through the variance. As in batch norm, $dx$ has no component along "shift the whole row" ($\sum_i dx_i = 0$), because adding a constant to a row doesn't change its normalized output.

**Why $\epsilon$ matters here.** A row whose features are all nearly equal has $\sigma^2 \approx 0$. Without $\epsilon$, $s$ would be huge and both `out` and `dx` would explode. The "big eps" case uses inputs scaled by 0.1 with `eps = 0.01`, where $\epsilon$ is comparable to $\sigma^2$ and must be in exactly the right place.

## 4. Trace an example by hand

**Example 1:** `x = [[1, 2, 3]]` is `(1, 3)`, `gamma = 1`, `beta = 0`, `dout = [[1, 0, 0]]`.

| quantity | value | shape |
|---|---|---|
| `mu`, `var` | `2`, `0.666667` | `(1, 1)` each |
| `inv_std` | `1.22473569` | `(1, 1)` |
| `x_hat` = `out` | `[[-1.2247, 0, 1.2247]]` | `(1, 3)` |
| `g = dout * gamma` | `[[1, 0, 0]]` | `(1, 3)` |
| `mean(g)` | `0.33333` | `(1, 1)` |
| `mean(g * x_hat)` | `-0.40825` | `(1, 1)` |
| `g - mean(g)` | `[[0.6667, -0.3333, -0.3333]]` | `(1, 3)` |
| `- x_hat * mean(g * x_hat)` | `[[-0.5, 0, 0.5]]` | `(1, 3)` |
| `dx` = `inv_std * (sum of the two rows above)` | `[[0.2041, -0.4082, 0.2041]]` | `(1, 3)` |
| `dgamma`, `dbeta` | `[-1.2247, 0, 0]`, `[1, 0, 0]` | `(3,)` each |

Pushing up `out[0]` alone means pushing `x[0]` up, but because the row is renormalized, raising `x[0]` also lowers its mean and changes the spread. The net effect is to lower `x[1]` and raise `x[2]` a little.

**Example 2** shows rows are independent: row 0 is `[0, 4]` (mean 2, variance 4), row 1 is `[1, 1.5]` (mean 1.25, variance 0.0625), and both normalize to about `[-1, 1]`. The parameter gradients sum over the two rows: `dbeta = [1 + 0.5, 1 - 0.5] = [1.5, 0.5]`.

## 5. Key idea: reduce over -1 for statistics, over the rest for parameters

```python
mu = x.mean(axis=-1, keepdims=True)      # (..., 1): one mean per row
lead = tuple(range(x.ndim - 1))          # every axis except the last
dbeta = dout.sum(axis=lead)              # (D,)
```

`lead` is `()` for 1-D input, `(0,)` for 2-D and `(0, 1)` for 3-D. `np.sum(axis=())` reduces over **no** axes and returns the array unchanged, which is exactly right for a single vector: `dbeta` is just `dout`. So one line covers all three shapes.

`keepdims=True` on the statistics keeps a trailing size-1 axis: `(B, T, 1)` for a `(B, T, D)` input. That broadcasts against `(B, T, D)` by stretching along the last axis, so each row is centered by its own mean. Without `keepdims` the mean is `(B, T)`, and `x - mu` tries to line `T` up with `D`.

`gamma` and `beta` are `(D,)`, and NumPy lines up trailing axes, so `gamma * x_hat` already scales feature `k` of every row by `gamma[k]`. No reshape is needed, unlike spatial batch norm.

## 6. Plan before you code

```
mu, var  = mean and biased variance over the last axis (keepdims)    # (..., 1)
inv_std  = 1 / sqrt(var + eps)                                       # (..., 1)
x_hat    = (x - mu) * inv_std                                        # (..., D)
out      = gamma * x_hat + beta                                      # (..., D)
lead     = all axes but the last
dbeta    = sum of dout over lead                                     # (D,)
dgamma   = sum of dout * x_hat over lead                             # (D,)
g        = dout * gamma                                              # (..., D)
dx       = inv_std * (g - mean_last(g) - x_hat * mean_last(g * x_hat))  # (..., D)
```

| reduction | axes | result shape |
|---|---|---|
| `mu`, `var`, the two means in `dx` | `-1`, `keepdims=True` | `(..., 1)` |
| `dgamma`, `dbeta` | `lead` | `(D,)` |

## 7. Build it one piece at a time

**Step 1: forward.**

```python
mu = x.mean(axis=-1, keepdims=True)        # (..., 1)
var = x.var(axis=-1, keepdims=True)        # (..., 1), biased
inv_std = 1.0 / np.sqrt(var + eps)         # (..., 1)
x_hat = (x - mu) * inv_std                 # (..., D)
out = gamma * x_hat + beta                 # (D,) broadcasts over leading axes
```

**Step 2: parameter gradients.**

```python
lead = tuple(range(x.ndim - 1))            # (), (0,) or (0, 1)
dbeta = dout.sum(axis=lead)                # (D,)
dgamma = (dout * x_hat).sum(axis=lead)     # (D,)
```

**Step 3: input gradient.**

```python
g = dout * gamma                                                   # (..., D)
dx = inv_std * (g - g.mean(axis=-1, keepdims=True)
                - x_hat * (g * x_hat).mean(axis=-1, keepdims=True))   # (..., D)
```

Note that `g` includes `gamma` **before** the means are taken. Each feature has its own `gamma[k]`, so `mean(g)` is not `gamma * mean(dout)`.

## 8. Full solution

```python
# NumPy for last-axis reductions and broadcasting
import numpy as np


# x, dout: (..., D); gamma, beta: (D,); returns (out, dx, dgamma, dbeta)
def layernorm(x, gamma, beta, dout, eps=1e-5):
    # (..., 1): each row's own mean over its D features
    mu = x.mean(axis=-1, keepdims=True)
    # (..., 1): each row's biased variance
    var = x.var(axis=-1, keepdims=True)
    # (..., 1): 1/sqrt(var + eps); eps keeps near-constant rows from blowing up
    inv_std = 1.0 / np.sqrt(var + eps)
    # (..., D): keepdims lets the per-row stats broadcast along the feature axis
    x_hat = (x - mu) * inv_std
    # (..., D): per-feature scale and shift; (D,) lines up with the last axis
    out = gamma * x_hat + beta

    # every axis except the last: () for 1-D input, so nothing is summed there
    lead = tuple(range(x.ndim - 1))
    # (D,) beta is used by every row, so its gradient sums over all leading positions
    dbeta = dout.sum(axis=lead)
    # (D,) gamma likewise, weighted by the normalized value it multiplied
    dgamma = (dout * x_hat).sum(axis=lead)

    # (..., D) gradient with respect to x_hat; gamma differs per feature, so apply it first
    g = dout * gamma
    # direct path minus the mean path minus the variance path, means over each row's features
    dx = inv_std * (g - g.mean(axis=-1, keepdims=True)
                    - x_hat * (g * x_hat).mean(axis=-1, keepdims=True))
    # forward output and the three gradients
    return out, dx, dgamma, dbeta
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `dx = [[0.2041, -0.4082, 0.2041]]` | all three gradient paths on one row |
| Example 2 | `dbeta = [1.5, 0.5]` | rows normalized independently; parameter grads sum over rows |
| single vector | `dbeta` equals `dout` | 1-D input: `lead = ()`, nothing summed |
| batch of sequences | `dgamma` shape `(8,)` | `(2, 4, 8)`: parameter grads sum over both leading axes |
| square 2d | `(5, 5)` | `N == D`, so the wrong axis still has the right shape |
| tall batch | `(20, 4)` | many rows, few features |
| big eps | `eps = 0.01`, inputs scaled by 0.1 | `eps` placement matters when the variance is small |
| 3d square | `(3, 3, 3)` | every axis the same size: only the right axes give the right numbers |

## 10. Complexity

A constant number of elementwise passes and reductions over the $n$ elements of `x`: $O(n)$ time and memory, the same order as the forward pass. For a transformer activation `(B, T, D)` that's $O(BTD)$, small next to the $O(BTD^2)$ of the surrounding matrix multiplies.

Layer norm is memory-bound, not compute-bound: it reads and writes the whole activation tensor for very little arithmetic. That's why it's one of the first operations to be fused into neighbouring kernels, and why RMSNorm, which drops the mean (and $\beta$), is popular in LLMs: one reduction instead of two.

## 11. If you got Wrong Answer

- **Example 1's `out` and `dx` are all zeros.** You took the statistics over axis 0 (`wrong_batch_axis.py`). With one row, each column has variance 0, so everything normalizes to 0. That's batch norm. It passes only "single vector", where axis 0 *is* the last axis.
- **Example 1's `dx` is `[[0.8165, -0.4082, -0.4082]]`.** You dropped the variance path: `dx = inv_std * (g - mean(g))` (`wrong_missing_var_term.py`).
- **2-D cases pass but "single vector", "batch of sequences" and "3d square" fail.** You summed the parameter gradients over axis 0 only (`wrong_param_grads_axis0.py`). For `(2, 4, 8)` that leaves a `(4, 8)` array; for a 1-D input it sums the features into one number.
- **A broadcast error, or wrong values only when sizes coincide.** You dropped `keepdims=True` on a statistic.

## 12. Follow-ups an interviewer might ask

- *Why do transformers use layer norm instead of batch norm?* Batch statistics over padded, variable-length sequences are unreliable; batch sizes per device are small; and autoregressive inference processes one token at a time. Layer norm uses nothing outside the current token.
- *What is RMSNorm?* $\text{out} = \gamma \odot x / \sqrt{\overline{x^2} + \epsilon}$: no mean subtraction and no $\beta$. Its backward pass drops the $\overline{g}$ term (problem 74, rmsnorm).
- *Pre-norm or post-norm?* Pre-norm, `x + f(LN(x))`, keeps an identity path through the residual stream and trains stably without warmup; most modern LLMs use it.
- *How is this related to batch norm's backward pass?* It's the same formula with the reduction axis swapped (problem 40, batchnorm-backward).
- *How would you test it?* Compare `dx` with central finite differences of `sum(dout * out)` (problem 46, numerical-gradient-check).
