Implement **RMSNorm** (Zhang & Sennrich, 2019), the normalization used in LLaMA, Mistral and most recent LLMs.

For each vector $x \in \mathbb{R}^d$ along the **last axis**:

$$
\operatorname{RMSNorm}(x)_i = \frac{x_i}{\sqrt{\frac{1}{d}\sum_{j=1}^{d} x_j^2 + \epsilon}} \cdot w_i
$$

Unlike LayerNorm, RMSNorm does **not** subtract the mean and has no bias. `eps` is added **inside** the square root.

Return an array with the same shape as `x`. Don't modify `x` in place.

**Constraints**

- `x` is a float array with `1 <= x.ndim <= 3`; the last axis has size `d`, `1 <= d <= 512`
- `weight` has shape `(d,)`
- `eps > 0`
