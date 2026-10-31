## Approach

The parameter gradients are the easy part. They sum over every element in the channel's group:

$$
d\beta = \sum dout, \qquad d\gamma = \sum dout \cdot \hat x
$$

For `dx`, let $g = dout \cdot \gamma$ be the gradient with respect to $\hat x$, and let $s = 1/\sqrt{\sigma^2 + \epsilon}$. Every $x_i$ in the group moves $\mu$ and $\sigma^2$, which in turn move every $\hat x_k$ in the group. Three paths reach $x_i$:

1. directly through $\hat x_i$, giving $g_i s$;
2. through $\mu$, giving $-\frac{s}{M}\sum_k g_k$;
3. through $\sigma^2$. Using $\partial \sigma^2/\partial x_i = \frac{2}{M}(x_i - \mu)$, this gives $-\frac{s}{M}\hat x_i \sum_k g_k \hat x_k$.

(The variance also depends on $\mu$, but $\sum_k (x_k - \mu) = 0$ makes that path vanish.) Adding them gives the compact formula:

$$
dx = s\left(g - \overline{g} - \hat x\, \overline{g \hat x}\right)
$$

where the bars are means over the group. In words, remove from $g$ its component along the constant direction and its component along $\hat x$, then rescale. Normalization is invariant to shifting and scaling $x$, so the gradient can't have components in those directions.

```python
axes = (0,) if x.ndim == 2 else (0, 2, 3)
mu = x.mean(axis=axes, keepdims=True)
s = 1 / np.sqrt(x.var(axis=axes, keepdims=True) + eps)
x_hat = (x - mu) * s
g = dout * gamma.reshape(1, -1, *[1] * (x.ndim - 2))
dx = s * (g - g.mean(axis=axes, keepdims=True)
          - x_hat * (g * x_hat).mean(axis=axes, keepdims=True))
```

For NCHW input, reducing over `(0, 2, 3)` with `keepdims=True` is the whole trick. It's the same as moving channels last, reshaping to `(N*H*W, C)` and running the 2-D version.

## Common mistakes

- **Treating $\mu$ and $\sigma^2$ as constants.** `dx = g * s` drops two of the three paths.
- **Keeping the mean path but not the variance path.** That's correct only if $g$ is orthogonal to $\hat x$, which it never is in practice.
- **Reducing only over axis 0 for 4-D input.** Spatial batch norm shares statistics across $H$ and $W$ too, so the reduction must include them.
- **`ddof=1`.** The forward pass used the biased variance, so the backward pass must too.

## Complexity

- **Time:** $O(n)$ for $n$ elements in `x`: a few elementwise passes and reductions.
- **Space:** $O(n)$ for `x_hat` and `dx`.
