## Approach

Layer norm uses the same normalization as batch norm, but it takes the statistics over the **feature axis of each example** instead of over the batch. Nothing depends on the batch size, so training and inference behave the same and no running averages are needed. That is why transformers use it.

Forward, with every reduction over the last axis:

```python
mu = x.mean(axis=-1, keepdims=True)
s = 1 / np.sqrt(x.var(axis=-1, keepdims=True) + eps)
x_hat = (x - mu) * s
out = gamma * x_hat + beta
```

Backward. `gamma` and `beta` are shared by every row, so their gradients sum over all leading axes:

$$
d\beta = \sum_{\text{rows}} dout, \qquad d\gamma = \sum_{\text{rows}} dout \odot \hat x
$$

For `dx`, let $g = dout \odot \gamma$. Within one row, every $x_k$ affects $\mu$ and $\sigma^2$, and through them every $\hat x$. Following the same three paths as in batch norm (direct, through the mean, through the variance) gives

$$
dx = s\left(g - \overline{g} - \hat x\,\overline{g \hat x}\right)
$$

with the bars now meaning means over the last axis:

```python
g = dout * gamma
dx = s * (g - g.mean(-1, keepdims=True) - x_hat * (g * x_hat).mean(-1, keepdims=True))
```

## Common mistakes

- **Normalizing over axis 0.** That's batch norm. On a `(N, D)` input it gives the right shape and the wrong numbers.
- **Summing `dgamma` over axis 0 only.** For a `(B, T, D)` input the parameter gradients must sum over both `B` and `T`.
- **Dropping the variance path.** `dx = s * (g - mean(g))` ignores how $\sigma^2$ moves with `x`.

## Complexity

- **Time:** $O(n)$ for $n$ elements in `x`.
- **Space:** $O(n)$ for `x_hat`, `out` and `dx`.
