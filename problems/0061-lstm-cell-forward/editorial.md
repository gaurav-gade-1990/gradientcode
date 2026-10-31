## Approach: one stacked product, then slice

All four gates are linear in the same two inputs, so compute them with one product and slice the result.

$$
z = x W + h_{t-1} U + b, \qquad [z_i, z_f, z_g, z_o] = \text{split}(z, 4)
$$

$$
c_t = \sigma(z_f) \odot c_{t-1} + \sigma(z_i) \odot \tanh(z_g), \qquad h_t = \sigma(z_o) \odot \tanh(c_t)
$$

```python
def sigmoid(a):
    e = np.exp(-np.abs(a))
    return np.where(a >= 0, 1.0 / (1.0 + e), e / (1.0 + e))

def lstm_cell(x, h_prev, c_prev, W, U, b):
    H = h_prev.shape[1]
    z = x @ W + h_prev @ U + b
    i = sigmoid(z[:, 0:H])
    f = sigmoid(z[:, H:2 * H])
    g = np.tanh(z[:, 2 * H:3 * H])
    o = sigmoid(z[:, 3 * H:4 * H])
    c = f * c_prev + i * g
    h = o * np.tanh(c)
    return h, c
```

The cell state $c$ is updated additively, so gradients pass through $f$ without being squashed by a nonlinearity on every step. That's why LSTMs remember longer than vanilla RNNs.

## Common mistakes

- **Wrong gate order.** Different libraries stack the gates differently. The spec says i, f, g, o. Swapping g and o puts a sigmoid where the tanh belongs.
- **Interleaved split.** `z.reshape(B, H, 4)` assumes the gates alternate column by column. The blocks are contiguous.
- **`h = o * c`.** The output is squashed: $h = o \odot \tanh(c)$.
- **Naive sigmoid.** `np.exp(a) / (1 + np.exp(a))` is `inf / inf = nan` at `a = 1000`.

## Complexity

- **Time:** $O(B \cdot 4H\,(d_{in} + H))$ for the two products. The elementwise work is $O(BH)$.
- **Space:** $O(BH)$ for the gates.
