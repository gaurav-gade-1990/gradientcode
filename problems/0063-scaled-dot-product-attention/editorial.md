## Approach: scores, mask, stable softmax, weighted sum

Each query scores every key with a dot product. Divide by $\sqrt{d_k}$, drop the masked pairs, turn each row into a distribution, and average the values with it.

$$
S = \frac{Q K^\top}{\sqrt{d_k}}, \qquad S_{ij} \leftarrow -\infty \text{ where } \text{mask}_{ij} = \text{False}, \qquad W = \operatorname{softmax}_{\text{row}}(S), \qquad O = W V
$$

```python
def attention(q, k, v, mask=None):
    d_k = q.shape[-1]
    scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d_k)
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)
    scores = scores - np.max(scores, axis=-1, keepdims=True)
    e = np.exp(scores)
    weights = e / np.sum(e, axis=-1, keepdims=True)
    return weights @ v, weights
```

`@` broadcasts over leading axes, and `np.swapaxes(k, -1, -2)` transposes only the last two, so the same code handles `(T, d)`, `(B, T, d)` and `(B, h, T, d)`. `np.where(mask, ...)` broadcasts the mask, so a `(T_q, T_k)` causal mask or a `(B, 1, 1, T_k)` padding mask both work.

### Why $\sqrt{d_k}$?

If the entries of $q$ and $k$ have unit variance, $q \cdot k$ has variance $d_k$. Dividing by $\sqrt{d_k}$ brings it back to $1$, which keeps the softmax away from its saturated, near-one-hot regime where gradients vanish.

### Why `-inf` before the softmax?

$e^{-\infty} = 0$ exactly, and the remaining weights renormalize among the kept keys. Because every row keeps at least one key, the row max is finite and nothing becomes `nan`.

## Common mistakes

- **No scaling, or scaling by $\sqrt{d_v}$.** The scale comes from the dimension of the dot product, which is $d_k$.
- **Masking after the softmax.** Multiplying the weights by the mask zeros the dropped pairs, but the rows no longer sum to $1$.
- **No max shift.** $e^{1000}$ overflows to `inf`, and the row becomes `nan`.
- **`k.T`** on a batched array reverses *all* axes, not just the last two.

## Complexity

- **Time:** $O(T_q T_k (d_k + d_v))$ per batch element.
- **Space:** $O(T_q T_k)$ for the score matrix. That quadratic term is what FlashAttention avoids by never materializing it.
