## Approach

LayerNorm does two things: it re-centers (subtracts the mean) and re-scales (divides by the standard deviation). RMSNorm keeps only the re-scaling. That is cheaper, with one reduction instead of two, and works just as well in practice, which is why LLaMA-style models use it.

$$
\operatorname{rms}(x) = \sqrt{\tfrac{1}{d}\textstyle\sum_j x_j^2 + \epsilon}, \qquad y = \frac{x}{\operatorname{rms}(x)} \odot w
$$

```python
def rmsnorm(x, weight, eps=1e-6):
    rms = np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + eps)
    return x / rms * weight
```

`keepdims=True` leaves a size-1 last axis so the per-row RMS broadcasts back over `x`. `weight` has shape `(d,)` and broadcasts against the last axis.

## Common mistakes

- **Subtracting the mean.** That's LayerNorm. On rows with a nonzero mean the result is different.
- **`eps` outside the square root.** `sqrt(ms) + eps` differs from `sqrt(ms + eps)` when activations are small, and an all-zero row is where the two disagree most.
- **Reducing over the whole array.** `np.mean(x * x)` without an axis normalizes every row by one global RMS.

## Complexity

- **Time:** $O(n)$ for $n$ elements: one pass to square and average, one to divide and scale.
- **Space:** $O(n)$ for the output plus $O(n/d)$ for the per-row RMS.
