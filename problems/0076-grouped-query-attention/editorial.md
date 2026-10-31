## Approach

Multi-head attention keeps a separate K and V per head, which makes the KV cache the memory bottleneck at inference. GQA shares each K/V head across a group of $g = n_q / n_{kv}$ query heads. $n_{kv} = n_q$ is ordinary MHA and $n_{kv} = 1$ is multi-query attention.

The cleanest implementation expands K and V to `n_q` heads and then runs ordinary causal attention:

```python
g = n_q // n_kv
k = np.repeat(k, g, axis=1)          # head h reads kv head h // g
v = np.repeat(v, g, axis=1)
s = q @ np.swapaxes(k, -1, -2) / np.sqrt(d)
s = np.where(np.triu(np.ones((T, T), bool), k=1), -np.inf, s)
s = s - s.max(axis=-1, keepdims=True)
w = np.exp(s)
out = (w / w.sum(axis=-1, keepdims=True)) @ v
```

Real kernels don't materialize the repeat. They reshape `q` to `(B, n_kv, g, T, d)` and broadcast against `k[:, :, None]`. The math is identical.

## Common mistakes

- **`np.tile` instead of `np.repeat`.** Tiling gives head $h$ the K/V head $h \bmod n_{kv}$. PyTorch's `repeat_interleave` and every GQA checkpoint use $\lfloor h/g \rfloor$.
- **Masking the diagonal.** The causal mask hides $j > i$ only. A token always attends to itself.
- **Forgetting $1/\sqrt{d}$.** The softmax gets too peaked.
- **Unstable softmax.** Large logits overflow `exp`. Subtract the row max after masking; every row keeps at least its diagonal, so the max is finite.

## Complexity

- **Time:** $O(B\, n_q\, T^2 d)$, the same as MHA.
- **Space:** $O(B\, n_q\, T^2)$ for the scores. The KV cache shrinks by a factor of $g$, which is the whole point.
