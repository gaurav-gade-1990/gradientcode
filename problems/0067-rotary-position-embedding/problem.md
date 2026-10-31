Apply **rotary position embedding** (RoPE, Su et al., 2021) to a query or key tensor, using the **half-split** layout of GPT-NeoX and Hugging Face LLaMA.

Let $d$ be the last dimension of `x`. Split the features into two halves, $x_1 = x[..., :d/2]$ and $x_2 = x[..., d/2:]$, so that feature $i$ is paired with feature $i + d/2$. For pair $i = 0, \dots, d/2 - 1$ and a token at position $p$:

$$
\theta_i = \text{base}^{-2i/d}, \qquad \phi = p \, \theta_i
$$

$$
\begin{aligned}
\text{out}[..., i] &= x_1[..., i] \cos\phi - x_2[..., i] \sin\phi \\
\text{out}[..., i + d/2] &= x_2[..., i] \cos\phi + x_1[..., i] \sin\phi
\end{aligned}
$$

This rotates each pair counterclockwise by the angle $\phi$.

- `x` has shape `(..., T, d)`, with zero or more leading axes (batch, heads).
- `positions` is an int array of shape `(T,)`. Token `t` (along axis `-2`) is at position `positions[t]`. Positions need not start at `0` or be contiguous. With a KV cache, for example, they start at the cache length.

Return an array with the same shape as `x`.

**Constraints**

- `d` is even and `2 <= d <= 32`
- `1 <= T <= 64`, `0 <= positions[t] <= 10^5`
- `0 <= len(...) <= 2`
