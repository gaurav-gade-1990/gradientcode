Run a **vanilla (Elman) RNN** with a $\tanh$ nonlinearity over a batch of sequences, and return every hidden state.

For each time step $t = 1, \dots, T$:

$$
h_t = \tanh\left(x_t W_{xh} + h_{t-1} W_{hh} + b\right)
$$

Vectors are rows, so `x[:, t] @ W_xh` has shape `(B, H)`.

- `x` has shape `(B, T, d_in)`. `x[:, t]` is the input at step $t$ (0-indexed in code).
- `h0` has shape `(B, H)`. It is the state before the first input.
- `W_xh` has shape `(d_in, H)`, `W_hh` has shape `(H, H)` and `b` has shape `(H,)`.

Return an array of shape `(B, T, H)` whose slice `[:, t]` is the state right after reading `x[:, t]`. Don't include `h0`.

**Constraints**

- `1 <= B <= 8`, `1 <= T <= 50`, `1 <= d_in, H <= 32`
- All inputs are float arrays
