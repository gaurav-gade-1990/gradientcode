Implement one step of an **LSTM** cell for a batch.

The four gates come from one stacked pre-activation:

$$
z = x W + h_{t-1} U + b \in \mathbb{R}^{B \times 4H}
$$

Split $z$ along its last axis into **four contiguous blocks** of width $H$, in the order **i, f, g, o** (PyTorch's order): `z[:, 0:H]` is the input gate, `z[:, H:2H]` the forget gate, `z[:, 2H:3H]` the candidate and `z[:, 3H:4H]` the output gate. Then

$$
\begin{aligned}
i &= \sigma(z_i), \quad f = \sigma(z_f), \quad g = \tanh(z_g), \quad o = \sigma(z_o) \\
c_t &= f \odot c_{t-1} + i \odot g \\
h_t &= o \odot \tanh(c_t)
\end{aligned}
$$

where $\sigma(a) = 1 / (1 + e^{-a})$.

- `x` has shape `(B, d_in)`, `h_prev` and `c_prev` have shape `(B, H)`.
- `W` has shape `(d_in, 4H)`, `U` has shape `(H, 4H)` and `b` has shape `(4H,)`.

Return a tuple `(h, c)` of two `(B, H)` arrays.

Pre-activations can be as large as `±1000`. Your sigmoid must not overflow or produce `nan`.

**Constraints**

- `1 <= B <= 8`, `1 <= d_in, H <= 32`
- All inputs are float arrays
