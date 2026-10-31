## Approach: project, split, attend in parallel, merge

Multi-head attention is ordinary attention run $h$ times on narrower slices of the same projections. The only real work is the reshaping.

$$
Q = xW_q \;\to\; (B, T, h, d_{head}) \;\to\; (B, h, T, d_{head}), \qquad O = \operatorname{concat}_j\left(\operatorname{softmax}\left(\tfrac{Q_j K_j^\top}{\sqrt{d_{head}}} + M\right) V_j\right) W_o
$$

```python
def multi_head_attention(x, W_q, W_k, W_v, W_o, num_heads, mask=None):
    B, T, d_model = x.shape
    d_head = d_model // num_heads

    def split(a):
        return a.reshape(B, T, num_heads, d_head).transpose(0, 2, 1, 3)

    q, k, v = split(x @ W_q), split(x @ W_k), split(x @ W_v)
    scores = q @ k.transpose(0, 1, 3, 2) / np.sqrt(d_head)
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)
    scores = scores - scores.max(axis=-1, keepdims=True)
    w = np.exp(scores)
    w = w / w.sum(axis=-1, keepdims=True)
    out = (w @ v).transpose(0, 2, 1, 3).reshape(B, T, d_model)
    return out @ W_o
```

With the heads on axis 1, one batched `@` computes every head's scores at once. A `(T, T)` mask broadcasts over both `B` and `h`.

### Why reshape then transpose?

In memory, row `(b, t)` of $Q$ holds head 0's features, then head 1's, and so on. `reshape(B, T, h, d_head)` exposes that layout without moving data. The transpose then makes the heads a batch axis. `reshape(B, h, T, d_head)` directly is legal NumPy but reinterprets the bytes: "head 1" would get the second half of the *tokens*, not the second slice of features. Merging has the same trap in reverse.

## Common mistakes

- **Scaling by $\sqrt{d_{model}}$.** Each head's dot product has length $d_{head}$, so that's the variance to correct for.
- **Reshaping without transposing**, on the split or on the merge.
- **Ignoring the mask**, which lets each token look at the future in a decoder.

## Complexity

- **Time:** $O(B T d_{model}^2)$ for the four projections plus $O(B T^2 d_{model})$ for attention, summed over heads.
- **Space:** $O(B h T^2)$ for the score tensor.

Splitting into heads costs nothing extra: the total width stays $d_{model}$. It buys $h$ independent attention patterns for the same compute.
