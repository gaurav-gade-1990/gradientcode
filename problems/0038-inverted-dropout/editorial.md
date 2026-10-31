## Approach

Dropout zeroes each activation with probability $1 - p$, where $p$ is `keep_prob`. On its own that shrinks the expected activation to $p\,x$. *Inverted* dropout fixes the scale during training instead of at test time:

$$
\mathbb{E}\left[\frac{x \cdot [u < p]}{p}\right] = \frac{x \cdot p}{p} = x
$$

Evaluation then needs no special case. The network sees the same expected scale it was trained on, so you return `x` as is.

```python
if not train:
    return x
mask = u < keep_prob
return x * mask / keep_prob
```

In a real layer you cache `mask` for the backward pass. The gradient is `dout * mask / keep_prob`, the same operation.

## Common mistakes

- **No rescaling.** The training-time output has expected value $p\,x$, which no longer matches evaluation.
- **`u <= keep_prob`.** The off-by-boundary keeps an element whose draw equals $p$. Stated masks must be followed exactly.
- **Scaling at eval time.** Multiplying by `keep_prob` at test time belongs to the original, non-inverted dropout. Doing it on top of the inverted version shrinks outputs twice.
- **Swapping keep and drop.** `u >= keep_prob` keeps elements with probability $1 - p$.

## Complexity

- **Time:** $O(n)$.
- **Space:** $O(n)$ for the mask and the output.
