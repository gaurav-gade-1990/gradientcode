## Approach: one matrix product per step

The state at step $t$ depends on the state at step $t-1$, so time has to be a Python loop. The batch dimension does not: each step is one `(B, d_in) @ (d_in, H)` product plus one `(B, H) @ (H, H)` product.

$$
h_t = \tanh\left(x_t W_{xh} + h_{t-1} W_{hh} + b\right)
$$

```python
def rnn_forward(x, h0, W_xh, W_hh, b):
    B, T, _ = x.shape
    h = h0
    states = np.empty((B, T, h0.shape[1]))
    for t in range(T):
        h = np.tanh(x[:, t] @ W_xh + h @ W_hh + b)
        states[:, t] = h
    return states
```

The input projection does not depend on $h$, so you can hoist it out of the loop: `xw = x @ W_xh + b` once, then `h = np.tanh(xw[:, t] + h @ W_hh)`. cuDNN does the same thing.

## Common mistakes

- **Transposing `W_hh`.** With row vectors the state multiplies from the left: `h @ W_hh`. Column-vector papers write $W_{hh} h$, which is `h @ W_hh.T` in this layout. Read the stated shapes.
- **Off by one.** Storing `h` before the update returns $h_0, \dots, h_{T-1}$ instead of $h_1, \dots, h_T$.
- **No recurrence.** Using `h0` at every step turns the RNN into a per-token MLP.

## Complexity

- **Time:** $O(T \cdot B \cdot H\,(d_{in} + H))$.
- **Space:** $O(B \cdot T \cdot H)$ for the returned states. The loop itself needs only the current $h$.

The sequential dependency is why RNNs train slowly on GPUs, and it is the main thing attention removes.
