Build the fixed **sinusoidal positional encoding** from "Attention Is All You Need".

For position $pos = 0, \dots, \text{max\_len} - 1$ and pair index $i = 0, \dots, d_{model}/2 - 1$:

$$
\begin{aligned}
PE[pos, 2i] &= \sin\left(\frac{pos}{\text{base}^{2i / d_{model}}}\right) \\
PE[pos, 2i + 1] &= \cos\left(\frac{pos}{\text{base}^{2i / d_{model}}}\right)
\end{aligned}
$$

The paper uses `base = 10000`. Even columns hold sines and odd columns hold cosines, and each sine shares its frequency with the cosine to its right.

Return a float array of shape `(max_len, d_model)`.

**Constraints**

- `1 <= max_len <= 512`
- `2 <= d_model <= 64`, and `d_model` is even
- `base > 1`
