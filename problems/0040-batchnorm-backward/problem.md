Implement the **backward pass of batch normalization** in training mode.

The forward pass normalized each channel with its own batch statistics, using the **biased** variance:

$$
\mu = \frac{1}{M}\sum x, \qquad \sigma^2 = \frac{1}{M}\sum (x - \mu)^2, \qquad
\hat x = \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}}, \qquad \text{out} = \gamma \hat x + \beta
$$

The sums run over a channel's **group** of $M$ elements, and `x` can have one of two layouts:

- **2-D `(N, D)`.** Channel `j` is the column `x[:, j]`, so $M = N$ and `gamma` has shape `(D,)`.
- **4-D `(N, C, H, W)`** (spatial batch norm, NCHW). Channel `c` is `x[:, c, :, :]`, so $M = N H W$ and `gamma` has shape `(C,)`.

You get the upstream gradient `dout` (same shape as `x`), the input `x`, `gamma` and `eps`. Recompute whatever you need from them. Remember that $\mu$ and $\sigma^2$ are functions of `x`.

Return a tuple `(dx, dgamma, dbeta)` with shapes `x.shape`, `gamma.shape` and `gamma.shape`.

**Constraints**

- `x.ndim` is 2 or 4; each group has `M >= 2` elements
- `x`, `dout` and `gamma` are float arrays; `eps > 0`
