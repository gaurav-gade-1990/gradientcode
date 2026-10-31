## Approach: two projections per step

Compute the input and hidden projections once per step, split each into r, z and n, and combine.

$$
r = \sigma(g^x_r + g^h_r), \quad z = \sigma(g^x_z + g^h_z), \quad n = \tanh(g^x_n + r \odot g^h_n), \quad h_t = (1 - z) \odot n + z \odot h_{t-1}
$$

```python
for t in range(T):
    gi = x[:, t] @ W_ih + b_ih
    gh = h @ W_hh + b_hh
    r = sigmoid(gi[:, :H] + gh[:, :H])
    z = sigmoid(gi[:, H:2 * H] + gh[:, H:2 * H])
    n = np.tanh(gi[:, 2 * H:] + r * gh[:, 2 * H:])
    h = (1 - z) * n + z * h
    states[:, t] = h
```

Keeping the hidden projection whole (bias included) and multiplying by $r$ afterwards is what lets cuDNN compute `h @ W_hh` for all three gates in one product. The original Cho et al. (2014) GRU applies $r$ to $h$ before the product, which gives a different result.

$z$ acts as an interpolation weight. Where $z = 1$ the unit copies its old state, and where $z = 0$ it takes the candidate.

## Common mistakes

- **Swapped interpolation.** `z * n + (1 - z) * h` is the other convention. It is self-consistent but not PyTorch's, and it gives different numbers.
- **Bias outside the reset gate.** `r * (h @ W_hn) + b_hn` drops the reset gate from the bias term. It only differs when `b_hh` is nonzero, so test with a nonzero `b_hh`.
- **Gate order.** The blocks are r, z, n. Reading z first swaps the roles of reset and update.

## Complexity

- **Time:** $O(T \cdot B \cdot 3H\,(d_{in} + H))$.
- **Space:** $O(BTH)$ for the output, $O(BH)$ working memory.

A GRU has three gate blocks to the LSTM's four and no separate cell state, so it is about 25% cheaper per step.
