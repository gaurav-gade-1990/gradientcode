## Approach: filter twice, renormalize each time, invert the CDF

Each step reshapes the distribution, and the next step reads the reshaped version, so the order is part of the spec.

$$
p = \operatorname{softmax}(z / T) \;\to\; \text{top-}k \;\to\; \text{renormalize} \;\to\; \text{top-}p \;\to\; \text{renormalize} \;\to\; \text{token} = \min\{i : F(i) > u\}
$$

```python
def sample_token(logits, temperature, top_k, top_p, u):
    z = logits / temperature
    p = np.exp(z - z.max())
    p = p / p.sum()
    order = np.argsort(-p, kind="stable")

    if 0 < top_k < len(p):
        keep = np.zeros(len(p), dtype=bool)
        keep[order[:top_k]] = True
        p = np.where(keep, p, 0.0)
        p = p / p.sum()

    if top_p < 1.0:
        cum = np.cumsum(p[order])
        n_keep = int(np.searchsorted(cum, top_p)) + 1
        keep = np.zeros(len(p), dtype=bool)
        keep[order[:n_keep]] = True
        p = np.where(keep, p, 0.0)
        p = p / p.sum()

    token = int(np.searchsorted(np.cumsum(p), u, side="right"))
    return min(token, len(p) - 1), p
```

One ranking is enough. Top-k zeros a suffix of it and renormalizing doesn't reorder anything, so the same `order` works for top-p. `np.searchsorted(cum, top_p)` returns the first position where `cum >= top_p`. Adding one turns that position into a count, so the crossing token is kept.

For sampling, `searchsorted(..., side="right")` finds the first index with $F(i) > u$. Zeroed tokens add nothing to the CDF, so they can never be picked. The `min` guards against the last cumulative value rounding to just below `1`.

### Why temperature divides

$T < 1$ stretches the logit gaps and sharpens the distribution. $T > 1$ flattens it, and $T \to 0$ approaches greedy decoding. Multiplying by $T$ inverts all of that.

## Common mistakes

- **Top-p on the original distribution.** After top-k, the survivors' probabilities are larger, so fewer of them are needed to reach `top_p`.
- **Dropping the crossing token.** `cum < top_p` keeps one token too few, and keeps nothing when the top token alone exceeds `top_p`.
- **Sampling in sorted order.** It's a valid sampler, but it maps `u` to a different token than the specified index-order CDF.
- **Unstable tie order.** `np.argsort(p)[::-1]` puts the *higher* index first among equal probabilities.

## Complexity

- **Time:** $O(V \log V)$ for the sort. With a large vocabulary, `np.argpartition` finds the top-k in $O(V)$, and you sort only those.
- **Space:** $O(V)$.
