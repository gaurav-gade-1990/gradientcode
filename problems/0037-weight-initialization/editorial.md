## Approach

Both schemes pick the weight variance so that activations (or gradients) keep roughly the same scale from layer to layer.

**Xavier/Glorot** balances the forward and backward passes and targets $\operatorname{Var}(W) = \frac{2}{\text{fan\_in} + \text{fan\_out}}$. A uniform distribution on $[-a, a]$ has variance $a^2/3$. Setting the two equal gives

$$
a = \sqrt{\frac{6}{\text{fan\_in} + \text{fan\_out}}}
$$

**He/Kaiming** accounts for ReLU zeroing half its inputs, which halves the variance. It doubles the fan-in rule: $\operatorname{Var}(W) = 2/\text{fan\_in}$.

Turning standard draws into the target distributions is an affine map: $U[0,1) \to U[-a, a)$ with $(2u - 1)a$, and $\mathcal{N}(0,1) \to \mathcal{N}(0, \sigma^2)$ with $\sigma z$.

```python
a = np.sqrt(6 / (fan_in + fan_out))
std = np.sqrt(2 / fan_in)
xavier = (2 * u - 1) * a
he = z * std
```

## Common mistakes

- **He with `fan_out`.** That's Kaiming's `fan_out` mode, which preserves gradient scale instead. The default (and this problem) uses `fan_in`.
- **Mixing up the two Xavier variants.** $\sqrt{2/(\text{fan\_in}+\text{fan\_out})}$ is the *std* of Xavier normal. The uniform *limit* is $\sqrt{3}$ times larger.
- **Forgetting to center.** `u * a` lands in $[0, a)$, so every weight is positive.

## Complexity

- **Time:** $O(\text{fan\_in} \cdot \text{fan\_out})$.
- **Space:** the same, for the two matrices.
