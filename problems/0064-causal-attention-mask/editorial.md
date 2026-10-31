## Approach: compare index grids

Give every row its absolute query position and every column its key position, then compare them with broadcasting.

$$
M_{ij} = 0 \text{ if } j \le i + \text{offset}, \text{ else } -\infty
$$

```python
def causal_mask(T_q, T_k, offset=0):
    i = np.arange(T_q)[:, None] + offset
    j = np.arange(T_k)[None, :]
    return np.where(j <= i, 0.0, -np.inf)
```

`np.triu(np.full((T_q, T_k), -np.inf), k=offset + 1)` does the same thing in one call, since `k` shifts the diagonal by the offset.

### Why the offset?

With a KV cache the keys include $P$ old tokens, but you only compute queries for the new ones. The new query in row $0$ is really at position $P$, so it must see keys $0 \dots P$, not just key $0$. Without the offset, decoding with a cache attends to the wrong keys and silently disagrees with the full forward pass.

### Why `-inf` and not `-1e9`?

For ordinary scores, `-1e9` gives a weight that underflows to $0$ anyway, so the difference is usually invisible. `-inf` is exact by construction, and it is what PyTorch's `generate_square_subsequent_mask` returns. In float16, `-1e9` isn't representable and becomes `-inf` on the cast.

## Common mistakes

- **Strict inequality.** `j < i` hides the diagonal, so a token can't see itself and row $0$ is all `-inf`, which makes the softmax return `nan`.
- **Ignoring the offset.** `np.tril` on a rectangle assumes the queries start at position $0$.

## Complexity

- **Time:** $O(T_q T_k)$.
- **Space:** $O(T_q T_k)$ for the mask.
