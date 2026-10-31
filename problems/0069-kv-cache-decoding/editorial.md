## Approach: append, then attend with an offset mask

Causal attention at row $t$ only needs $q_t$ and the keys and values of rows $0 \dots t$. Those past keys and values never change, so you store them and compute only the new rows' projections.

Each call does four things:

1. Project the $n$ new tokens to $q$, $k$, $v$ and split heads: `(n, d) -> (h, n, d_head)`.
2. **Append** $k$ and $v$ to the cache along the length axis, so it now holds $P + n$ entries.
3. Score the $n$ queries against all $P + n$ keys. Query $i$ is at position $P + i$, so it may see key $j$ when $j \le P + i$.
4. Run a stable softmax, take the weighted sum of values, merge the heads and multiply by $W_o$.

```python
def prefill(self, x):
    n = x.shape[0]
    P = self.K.shape[1]
    q = self._split(x @ self.W_q)
    self.K = np.concatenate([self.K, self._split(x @ self.W_k)], axis=1)
    self.V = np.concatenate([self.V, self._split(x @ self.W_v)], axis=1)
    s = q @ self.K.transpose(0, 2, 1) / np.sqrt(self.dh)
    allowed = np.arange(P + n)[None, :] <= (P + np.arange(n))[:, None]
    s = np.where(allowed, s, -np.inf)
    s = s - s.max(axis=-1, keepdims=True)
    w = np.exp(s)
    w = w / w.sum(axis=-1, keepdims=True)
    return (w @ self.V).transpose(1, 0, 2).reshape(n, -1) @ self.W_o

def step(self, x_t):
    return self.prefill(x_t[None, :])[0]
```

For a single step the mask is all `True`, since the newest token may see everything. The mask only matters inside a multi-token prefill, and that's where the offset $P$ comes in.

Real implementations preallocate a `(max_len, h, d_head)` buffer and write into it, instead of concatenating, which copies the cache every step.

## Common mistakes

- **Attending before appending.** The new token then can't see its own key. On the very first token the softmax is over nothing.
- **No mask in prefill.** Within a block, token $0$ would see tokens $1 \dots n-1$. It only matters when $n > 1$, which is why tests that only `step` pass anyway.
- **Mask without the offset.** `j <= i` instead of `j <= P + i` hides the cached tokens from a prefill that follows earlier calls.
- **Cache as a class attribute.** `keys = []` in the class body is shared by every instance, so two sequences decoded side by side read each other's keys.

## Complexity

- **Time:** a step costs $O(d^2)$ for the projections plus $O(L d)$ for attention over $L$ cached tokens. Without a cache you redo $O(L d^2 + L^2 d)$ work for every new token.
- **Space:** $O(L d)$ per sequence for the cache. At scale that's $2 \cdot \text{layers} \cdot L \cdot d$ numbers per sequence, which is why grouped-query attention shares keys and values across heads.
