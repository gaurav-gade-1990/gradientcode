## Approach: one outer product of positions and frequencies

Every column pair is a sine and cosine wave at one frequency. The frequencies fall geometrically from $1$ to about $1/\text{base}$ across the pairs.

$$
\omega_i = \text{base}^{-2i / d_{model}}, \qquad PE[pos, 2i] = \sin(pos \cdot \omega_i), \qquad PE[pos, 2i+1] = \cos(pos \cdot \omega_i)
$$

```python
def positional_encoding(max_len, d_model, base=10000.0):
    pos = np.arange(max_len)[:, None]
    freq = base ** (-np.arange(0, d_model, 2) / d_model)
    angles = pos * freq[None, :]
    pe = np.empty((max_len, d_model))
    pe[:, 0::2] = np.sin(angles)
    pe[:, 1::2] = np.cos(angles)
    return pe
```

`np.arange(0, d_model, 2)` gives $2i$ directly, so the exponent needs no extra factor of two.

### Why sines and cosines?

For any fixed offset $k$, $PE[pos + k]$ is a rotation of $PE[pos]$ in each $(\sin, \cos)$ pair, and the rotation angle depends only on $k$. A linear layer can therefore learn to attend by relative position. RoPE takes this idea and applies the rotation directly to queries and keys.

## Common mistakes

- **Concatenating** all the sines, then all the cosines. Some codebases (tensor2tensor) do this, and it works for training, but it isn't the layout in the paper and its columns differ.
- **Exponent $i / d$ instead of $2i / d$.** The frequencies then only fall to $\text{base}^{-1/2}$ across the dimensions.

## Complexity

- **Time:** $O(\text{max\_len} \cdot d_{model})$.
- **Space:** $O(\text{max\_len} \cdot d_{model})$. In practice it's computed once and cached.
