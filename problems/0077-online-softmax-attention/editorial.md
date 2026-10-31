## Approach

Softmax needs the row max (for stability) and the row sum (to normalize), and both seem to require all the scores at once. The **online softmax** trick removes that requirement. Keep a running max $m$ and a running sum $\ell = \sum e^{s_j - m}$. When a new max $m'$ arrives, every old term $e^{s_j - m}$ should have been $e^{s_j - m'}$, which is the old term times $e^{m - m'}$. One multiplication fixes the whole sum:

$$
\ell' = e^{m - m'}\,\ell + \sum_{j \in \text{block}} e^{s_j - m'}
$$

The output works the same way. Keep the **unnormalized** accumulator $a = \sum e^{s_j - m} v_j$, rescale it by the same factor, and divide by $\ell$ only at the end.

```python
for b in range(n_blocks):
    s = Q @ K[j0:j1].T / np.sqrt(d)
    if causal:
        s = np.where(np.arange(j0, j1)[None, :] <= rows, s, -np.inf)
    m_new = np.maximum(m, s.max(axis=1))
    p = np.exp(s - m_new[:, None])
    corr = np.exp(m - m_new)           # exp(-inf) = 0 on the first block
    l = corr * l + p.sum(axis=1)
    acc = corr[:, None] * acc + p @ V[j0:j1]
    m = m_new
O = acc / l[:, None]
```

FlashAttention also tiles the queries and keeps each tile in on-chip SRAM. The algorithm per query row is exactly this loop. Memory traffic drops from $O(T^2)$ to $O(T d)$ per head, and the stored $(m, \ell)$ (as $m + \log \ell$, the log-sum-exp) is all the backward pass needs to recompute the scores.

## Common mistakes

- **Not rescaling `acc`.** Old contributions keep their stale scale, so the output is a mix of differently scaled terms.
- **Not rescaling `l`.** The output no longer sums its weights to 1.
- **Recording the block's own max.** The running max is the max over every block so far.
- **Computing full attention.** `O` matches, but the per-block statistics don't: the running max after block 0 only knows about block 0.
- **Causal mask with local indices.** Inside block $b$ the key's position is `j0 + c`, not `c`.

## Complexity

- **Time:** $O(T_q T_k d)$, the same FLOPs as standard attention, plus $O(T_q T_k)$ for the rescaling.
- **Space:** $O(T_q \cdot \texttt{block\_size})$ for one score tile plus $O(T_q d_v)$ for the accumulator, instead of $O(T_q T_k)$.
