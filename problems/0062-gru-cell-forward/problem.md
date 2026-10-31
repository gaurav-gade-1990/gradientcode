Run a **GRU** over a batch of sequences using PyTorch's formulation, and return every hidden state.

The input and hidden projections are each stacked in the order **r, z, n** as three contiguous blocks of width $H$:

$$
g^{x} = x_t W_{ih} + b_{ih}, \qquad g^{h} = h_{t-1} W_{hh} + b_{hh} \qquad (\text{both } B \times 3H)
$$

with $g_r = g[:, 0{:}H]$, $g_z = g[:, H{:}2H]$, $g_n = g[:, 2H{:}3H]$. Then

$$
\begin{aligned}
r &= \sigma(g^x_r + g^h_r) \\
z &= \sigma(g^x_z + g^h_z) \\
n &= \tanh\left(g^x_n + r \odot g^h_n\right) \\
h_t &= (1 - z) \odot n + z \odot h_{t-1}
\end{aligned}
$$

Note that the reset gate multiplies $g^h_n = h_{t-1} W_{hn} + b_{hn}$, **including** its bias.

- `x` has shape `(B, T, d_in)` and `h0` has shape `(B, H)`.
- `W_ih` has shape `(d_in, 3H)`, `W_hh` has shape `(H, 3H)`, and `b_ih`, `b_hh` have shape `(3H,)`.

Return an array of shape `(B, T, H)` whose slice `[:, t]` is the state after reading `x[:, t]`. Don't include `h0`.

**Constraints**

- `1 <= B <= 8`, `1 <= T <= 40`, `1 <= d_in, H <= 16`
- Pre-activations stay within `±50`
