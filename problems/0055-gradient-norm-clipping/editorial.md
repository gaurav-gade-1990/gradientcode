## Approach

One bad batch can produce a huge gradient and wreck training. Clipping by the **global** norm caps the size of the update and keeps its direction. All parameters are scaled by the same factor, so the update still points the way the full gradient points.

$$
\|g\| = \sqrt{\textstyle\sum_k \|g_k\|^2}, \qquad c = \min\!\left(1, \frac{\tau}{\|g\| + 10^{-6}}\right), \qquad g_k \leftarrow c\, g_k
$$

```python
def clip_grad_norm(grads, max_norm):
    total_norm = float(np.sqrt(sum(np.sum(g * g) for g in grads)))
    coef = min(1.0, max_norm / (total_norm + 1e-6))
    return [g * coef for g in grads], total_norm
```

Returning the pre-clip norm is useful in practice. Logging it is the standard way to spot loss spikes.

## Common mistakes

- **Per-tensor clipping.** Clipping each array by its own norm rotates the overall gradient. It is a different (rarely wanted) method.
- **No clamp.** Without `min(1, ...)`, every update is rescaled to norm `max_norm`, so small, healthy gradients get scaled up.
- **Reporting the clipped norm.** `clip_grad_norm_` returns the norm before clipping. After clipping it would just be about `max_norm`.

## Complexity

- **Time:** $O(n)$ for $n$ gradient elements in total: one pass for the norm, one for the scaling.
- **Space:** $O(n)$ for the clipped copies.
