## 1. What the problem is really asking

Problem 39 built batch norm's forward pass. This one asks for the backward pass: given `dout` $= \partial L / \partial\, \text{out}$, return the gradients for the input `x` and for the parameters `gamma` and `beta`.

The parameter gradients are one line each. The hard part is `dx`, because **the batch mean and variance are functions of `x`**. Nudge one sample and you move the mean and variance of its whole group, which moves every normalized value in that group. A correct `dx` has to follow all three paths from $x_i$ to the loss. The answer collapses to a short formula:

$$dx = \frac{1}{\sqrt{\sigma^2 + \epsilon}}\Big(g - \overline{g} - \hat x\,\overline{g \hat x}\Big), \qquad g = \gamma \cdot dout,$$

where the bars are means over the group. Under the story, it's **a gradient projection**: take the upstream gradient, remove its components along "shift everything" and "scale everything", and rescale.

It also has to work for two layouts: `(N, D)` and spatial batch norm on `(N, C, H, W)`. The judge compares `(dx, dgamma, dbeta)` with `rtol=1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `dout` | same as `x` | upstream gradient | the starting point for all three |
| `x` | `(N, D)` or `(N, C, H, W)` | the forward-pass input | recompute `mu`, `var`, `x_hat` |
| `gamma` | `(D,)` or `(C,)` | the learned scale | `g = dout * gamma` |
| `eps` | float, default `1e-5` | the forward pass's constant | inside the square root |
| return | `x.shape`, `gamma.shape`, `gamma.shape` | `dx, dgamma, dbeta` | |

A channel's **group** is every element that shares its statistics: the column `x[:, j]` for 2-D, so $M = N$, and the slab `x[:, c, :, :]` for 4-D, so $M = NHW$.

The details that are easy to miss:

- **You only get `x`, not the forward cache.** Recompute `mu`, `var` and `x_hat` exactly as the forward pass did, with the biased variance.
- **For 4-D, reduce over `(0, 2, 3)`.** Reducing over axis 0 alone gives per-pixel statistics, which is not spatial batch norm.
- **`gamma` must be reshaped to broadcast.** `(C,)` against `(N, C, H, W)` lines up with `W`, not `C`. Reshape it to `(1, C, 1, 1)`.

## 3. The math

Fix one channel and write its group as $x_1, \dots, x_M$. The forward pass is

$$\mu = \frac1M \sum_k x_k, \quad \sigma^2 = \frac1M \sum_k (x_k - \mu)^2, \quad s = (\sigma^2 + \epsilon)^{-1/2}, \quad \hat x_k = (x_k - \mu)\,s, \quad \text{out}_k = \gamma \hat x_k + \beta.$$

**Parameter gradients.** $\partial\, \text{out}_k / \partial \beta = 1$ and $\partial\, \text{out}_k / \partial \gamma = \hat x_k$. Both parameters are shared by the whole group, so their gradients sum:

$$d\beta = \sum_k dout_k, \qquad d\gamma = \sum_k dout_k\, \hat x_k.$$

**Gradient into $\hat x$.** $g_k = \partial L / \partial \hat x_k = \gamma\, dout_k$.

**Gradient into $x_i$.** $\hat x_k$ depends on $x_i$ directly (when $k = i$), through $\mu$, and through $s$ (via $\sigma^2$). By the chain rule,

$$\frac{\partial L}{\partial x_i} = \sum_k g_k \frac{\partial \hat x_k}{\partial x_i}.$$

Differentiate $\hat x_k = (x_k - \mu) s$ with respect to $x_i$:

$$\frac{\partial \hat x_k}{\partial x_i} = \Big([k = i] - \frac{\partial \mu}{\partial x_i}\Big) s + (x_k - \mu) \frac{\partial s}{\partial x_i}.$$

The pieces:

- $\partial \mu / \partial x_i = 1/M$.
- $\partial \sigma^2 / \partial x_i = \frac{2}{M}(x_i - \mu) - \frac{2}{M}\sum_k (x_k - \mu)\cdot\frac{1}{M}$. The second term is 0 because deviations from the mean sum to 0. So $\partial \sigma^2 / \partial x_i = \frac2M (x_i - \mu)$.
- $\partial s / \partial \sigma^2 = -\tfrac12 (\sigma^2 + \epsilon)^{-3/2} = -\tfrac12 s^3$, so $\partial s / \partial x_i = -\tfrac12 s^3 \cdot \frac2M (x_i - \mu) = -\frac{s^2}{M}\,\hat x_i$, using $(x_i - \mu) s = \hat x_i$.

Substitute, and use $(x_k - \mu) = \hat x_k / s$:

$$\frac{\partial \hat x_k}{\partial x_i} = s\,[k = i] - \frac{s}{M} - \frac{\hat x_k}{s}\cdot\frac{s^2}{M}\hat x_i = s\Big([k = i] - \frac1M - \frac{\hat x_k \hat x_i}{M}\Big).$$

Now sum against $g_k$:

$$\frac{\partial L}{\partial x_i} = s\Big(g_i - \frac1M \sum_k g_k - \hat x_i\, \frac1M \sum_k g_k \hat x_k\Big) = s\big(g_i - \overline{g} - \hat x_i\,\overline{g \hat x}\big).$$

The three terms are the three paths: direct, through $\mu$, through $\sigma^2$.

**What the formula says.** It's $s$ times $g$ with its mean removed and its projection onto $\hat x$ removed (when $\epsilon \to 0$, $\overline{\hat x^2} = 1$, so $\hat x\,\overline{g\hat x}$ is exactly that projection). The output of normalization doesn't change if you add a constant to the whole group or scale the whole group, so the gradient can have **no component** in those two directions. Two checks follow: $\sum_i dx_i = 0$ always, and $\sum_i dx_i \hat x_i \approx 0$ (exactly 0 only as $\epsilon \to 0$).

## 4. Trace an example by hand

**Example 1:** one column, `x = [1, 2, 3]`, `dout = [1, 0, -1]`, `gamma = [1]`. Shapes are `(3, 1)` and `(1,)`.

| quantity | value |
|---|---|
| `mu`, `var` | `2`, `0.666667` |
| `inv_std` | `1.22473569` |
| `x_hat` | `[-1.2247, 0, 1.2247]` |
| `dbeta = sum(dout)` | `0` |
| `dgamma = sum(dout * x_hat)` | `-2.4495` |
| `mean(g)`, `mean(g * x_hat)` | `0`, `-0.81649` |
| `dx` | `[1.837e-5, 0, -1.837e-5]` |

`dout` is exactly $-0.8165\,\hat x$, a pure "scale the group" direction, so the projection removes it entirely and `dx` is zero up to the `eps` effect. Treating the statistics as constants would give `g * inv_std = [1.2247, 0, -1.2247]`.

**A scratch example where all three paths show:** `x = [1, 2, 4]`, `dout = [1, 0, 0]`, `gamma = [1]`.

| quantity | value |
|---|---|
| `mu`, `var`, `inv_std` | `2.3333`, `1.5556`, `0.80178` |
| `x_hat` | `[-1.06904, -0.26726, 1.33630]` |
| `mean(g)`, `mean(g * x_hat)` | `0.33333`, `-0.35635` |
| path 1, `s * g` | `[0.80178, 0, 0]` |
| path 2, `-s * mean(g)` | `[-0.26726, -0.26726, -0.26726]` |
| path 3, `-s * x_hat * mean(g * x_hat)` | `[-0.30544, -0.07636, 0.38180]` |
| `dx` (sum) | `[0.22908, -0.34362, 0.11454]` |

Central finite differences on the forward pass give `[0.229082, -0.34362, 0.114538]`, matching. The entries of `dx` sum to `-4e-17`, i.e. zero.

**Example 2** has `N = 2`. With two points, normalization always maps them to about $\pm 1$ whatever their values, so `x` barely affects the output and `dx` is close to 0 in both columns; only `dgamma = [-0.5, -3]` and `dbeta = [1.5, 1]` are non-trivial.

## 5. Key idea: one code path for both layouts with keepdims

Choose the reduction axes and the `gamma` shape once:

| layout | `axes` | `gamma` reshaped to | `mu` shape (keepdims) |
|---|---|---|---|
| `(N, D)` | `(0,)` | `(1, D)` | `(1, D)` |
| `(N, C, H, W)` | `(0, 2, 3)` | `(1, C, 1, 1)` | `(1, C, 1, 1)` |

With `keepdims=True`, every statistic keeps a size-1 axis wherever it was reduced, so it broadcasts back against `x` with no further reshaping. Without `keepdims`, a 4-D mean would be `(C,)`, and `x - mu` would line `C` up with `W`: a broadcast error, or silently wrong values when `C == W`.

The parameter gradients use the same `axes` **without** `keepdims`, which gives exactly `gamma.shape`.

## 6. Plan before you code

```
axes, shape = (0,), (1, -1)            for 2-D
            = (0, 2, 3), (1, -1, 1, 1) for 4-D
mu, var  = mean and biased variance over axes (keepdims)
inv_std  = 1 / sqrt(var + eps)
x_hat    = (x - mu) * inv_std
dbeta    = sum of dout over axes
dgamma   = sum of dout * x_hat over axes
g        = dout * gamma reshaped
dx       = inv_std * (g - mean(g) - x_hat * mean(g * x_hat))
```

## 7. Build it one piece at a time

**Step 1: axes and shapes.**

```python
if x.ndim == 2:
    axes, shape = (0,), (1, -1)              # group = a column
else:
    axes, shape = (0, 2, 3), (1, -1, 1, 1)   # group = one channel across N, H, W
```

**Step 2: recompute the forward statistics.**

```python
mu = x.mean(axis=axes, keepdims=True)        # (1, D) or (1, C, 1, 1)
var = x.var(axis=axes, keepdims=True)        # same; biased, as in the forward pass
inv_std = 1.0 / np.sqrt(var + eps)           # same
x_hat = (x - mu) * inv_std                   # x.shape
```

**Step 3: the parameter gradients.**

```python
dbeta = dout.sum(axis=axes)                  # (D,) or (C,)
dgamma = (dout * x_hat).sum(axis=axes)       # (D,) or (C,)
```

**Step 4: the input gradient.**

```python
g = dout * gamma.reshape(shape)              # x.shape: dL/dx_hat
dx = inv_std * (g - g.mean(axis=axes, keepdims=True)
                - x_hat * (g * x_hat).mean(axis=axes, keepdims=True))   # x.shape
```

Each `mean(..., keepdims=True)` is one number per channel, broadcast back to every element of that channel's group. On a scratch 4-D input `(2, 3, 4, 4)`, a finite-difference check of one entry gave `-0.0687107047` against the formula's `-0.0687107075`.

## 8. Full solution

```python
# NumPy for grouped reductions and broadcasting
import numpy as np


# dout, x: (N, D) or (N, C, H, W); gamma: (D,) or (C,); returns (dx, dgamma, dbeta)
def batchnorm_backward(dout, x, gamma, eps=1e-5):
    # 2-D: each column is one channel's group
    if x.ndim == 2:
        # reduce over the batch axis; gamma becomes a (1, D) row
        axes, shape = (0,), (1, -1)
    # 4-D NCHW: a channel's group spans batch and both spatial axes
    else:
        # reduce over N, H, W; gamma becomes (1, C, 1, 1) so it lines up with the channel axis
        axes, shape = (0, 2, 3), (1, -1, 1, 1)
    # per-channel mean, keepdims so it broadcasts back against x
    mu = x.mean(axis=axes, keepdims=True)
    # per-channel biased variance, matching the forward pass
    var = x.var(axis=axes, keepdims=True)
    # s = 1/sqrt(var + eps), the forward pass's scale
    inv_std = 1.0 / np.sqrt(var + eps)
    # x.shape: the normalized values the forward pass produced
    x_hat = (x - mu) * inv_std

    # beta is shared by the whole group, so its gradient sums dout over it -> gamma.shape
    dbeta = dout.sum(axis=axes)
    # out = gamma * x_hat + beta, so dgamma sums dout * x_hat over the group -> gamma.shape
    dgamma = (dout * x_hat).sum(axis=axes)

    # x.shape: gradient with respect to x_hat
    g = dout * gamma.reshape(shape)
    # direct path, minus the mean path, minus the variance path, all scaled by inv_std
    dx = inv_std * (g - g.mean(axis=axes, keepdims=True)
                    - x_hat * (g * x_hat).mean(axis=axes, keepdims=True))
    # each gradient has the shape of the thing it's the gradient of
    return dx, dgamma, dbeta
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `dx ≈ 0`, `dgamma = [-2.4495]`, `dbeta = [0]` | `dout` along `x_hat` is cancelled by the variance path |
| Example 2 | `dx ≈ 0`, `dgamma = [-0.5, -3]`, `dbeta = [1.5, 1]` | `N = 2`; parameter gradients sum over rows |
| random 2d | `dgamma[0] = -4.0515` | the full formula on `(8, 5)` |
| random 4d | `dbeta = [3.0169, 3.0483, 8.9352]` | spatial batch norm: reduce over `(0, 2, 3)` |
| 4d single sample | `dbeta = [-2.2522, -2.1028]` | `N = 1` but `M = 9`: the group is spatial |
| 4d non-square spatial | `dgamma` shape `(4,)` | `H = 2`, `W = 5`, `C = 4`: axes must be right |
| big eps | `dgamma = [0.05, -0.5346, -0.3163]` | `eps = 0.05` with tiny-variance inputs: `eps` must match the forward pass |
| large batch | `dbeta[1] = -17.6085` | `(64, 4)` |

## 10. Complexity

A constant number of elementwise passes and per-channel reductions over all $n$ elements of `x`: $O(n)$ time and $O(n)$ memory for `x_hat`, `g` and `dx`. The backward pass costs about the same as the forward pass.

In a framework you'd cache `x_hat` and `inv_std` from the forward pass instead of recomputing them; they cost one tensor and one per-channel vector. The compact formula is also faster than backpropagating through the computational graph step by step (subtract, square, mean, sqrt, divide), which allocates an intermediate for every step. Fused kernels compute the two per-channel means $\overline{g}$ and $\overline{g \hat x}$ in one pass, then `dx` in a second.

## 11. If you got Wrong Answer

- **Example 1's `dx` is `[1.2247, 0, -1.2247]` instead of about 0.** You backpropagated through `x_hat` as if `mu` and `var` were constants (`wrong_constant_stats.py`). It fails all eight cases.
- **Example 1's `dx` is still `[1.2247, 0, -1.2247]` even though you subtracted `mean(g)`.** You included the mean path but not the variance path (`wrong_missing_var_term.py`). Here `mean(g) = 0`, so only the variance term could cancel `g`.
- **`dgamma` in Example 1 is `-2` instead of `-2.4495`.** You used `ddof=1` (`wrong_unbiased_var.py`). The forward pass used the biased variance; the backward pass must match.
- **2-D cases pass, every 4-D case fails.** You reduced over axis 0 only (`wrong_2d_only.py`), which normalizes per pixel instead of per channel.
- **A broadcast error on 4-D input.** You multiplied by `gamma` without reshaping it to `(1, C, 1, 1)`.

## 12. Follow-ups an interviewer might ask

- *How do you verify a backward pass like this?* Central finite differences on a tiny input, as in section 7 (problem 46, numerical-gradient-check).
- *Why do the gradient entries of a group sum to zero?* Shifting the whole group by a constant doesn't change the normalized output, so the loss has zero derivative in the all-ones direction.
- *How does layer norm's backward pass differ?* The formula is identical; only the reduction axis changes, to the feature axis of each example (problem 41, layernorm-forward-backward).
- *What's the backward pass in eval mode?* The running statistics are constants, so the layer is affine and `dx = dout * gamma / sqrt(running_var + eps)`.
- *Can you write `dx` without `x_hat`?* Yes, by expanding `x_hat = (x - mu) * inv_std`, but the `x_hat` form needs fewer operations and is the one frameworks use.
