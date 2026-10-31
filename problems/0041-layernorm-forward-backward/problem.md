Implement the forward and backward pass of **layer normalization** over the last axis.

`x` has shape `(..., D)`. Each vector along the last axis is normalized with its own mean and **biased** variance:

$$
\mu = \frac{1}{D}\sum_{k=1}^{D} x_k, \qquad \sigma^2 = \frac{1}{D}\sum_{k=1}^{D} (x_k - \mu)^2, \qquad
\hat x = \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}}
$$

$$
\text{out} = \gamma \odot \hat x + \beta
$$

where `gamma` and `beta` have shape `(D,)` and broadcast over the leading axes.

You also get `dout` $= \partial L / \partial\, \text{out}$ with the same shape as `x`. Compute `dx`, `dgamma` and `dbeta`. Remember that $\mu$ and $\sigma^2$ depend on `x`.

Return a tuple `(out, dx, dgamma, dbeta)` with shapes `x.shape`, `x.shape`, `(D,)` and `(D,)`.

**Constraints**

- `1 <= x.ndim <= 3`, `2 <= D <= 64`
- `x`, `gamma`, `beta` and `dout` are float arrays; `eps > 0`
