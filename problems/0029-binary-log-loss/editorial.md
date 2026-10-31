## Approach: clip, then average

The loss is the negative log-likelihood of the labels under a Bernoulli model with success probability $p_i$. For $y = 1$ only the $\log p$ term survives; for $y = 0$ only $\log(1 - p)$.

A model that outputs exactly `0` for a positive gets $-\log 0 = \infty$. Clipping into $[\epsilon, 1 - \epsilon]$ caps any one sample's loss at $-\log \epsilon \approx 34.5$ for $\epsilon = 10^{-15}$:

```python
def log_loss(y_true, p, eps=1e-15):
    y = y_true.astype(float)
    q = np.clip(p, eps, 1 - eps)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))
```

### Losses from logits

When you have logits $z$ instead of probabilities, skip the clip and use the stable form $\max(z, 0) - z y + \log(1 + e^{-|z|})$. That is what `BCEWithLogitsLoss` does, and it is why frameworks prefer you pass logits.

## Common mistakes

- **No clipping.** One confident wrong prediction makes the mean `inf`. Even `0 * log(0)` is `nan`, so a confident right prediction breaks it too.
- **Clipping only one side.** `p = 1` for a negative still hits `log(0)`. Clip both ends.
- **Sum instead of mean.** The loss then scales with the dataset size.

## Complexity

- **Time:** $O(n)$.
- **Space:** $O(n)$ for the clipped copy.
