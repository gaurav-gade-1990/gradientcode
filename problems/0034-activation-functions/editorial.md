## Approach

Every function here is elementwise, so each one is a single vectorized NumPy expression. Reuse the forward value in the derivative whenever you can.

**Sigmoid.** $\sigma' = \sigma(1-\sigma)$. For stability, never call `exp` on a large positive number. With $e = e^{-|x|} \in (0, 1]$:

$$
\sigma(x) = \begin{cases} 1/(1+e) & x \ge 0 \\ e/(1+e) & x < 0 \end{cases}
$$

**Tanh.** $\tanh' = 1 - \tanh^2$.

**ReLU and Leaky ReLU.** The kink at $0$ has no derivative, so frameworks pick a convention. PyTorch uses the left side: $0$ for ReLU and $\alpha$ for Leaky ReLU. That means testing `x > 0`.

**GELU (tanh approximation).** With $u = c(x + 0.044715x^3)$ and $t = \tanh u$, the product rule gives

$$
\operatorname{gelu}'(x) = \tfrac12(1 + t) + \tfrac12\,x\,(1 - t^2)\,c\,(1 + 3 \cdot 0.044715\,x^2)
$$

```python
s = stable_sigmoid(x)
t = np.tanh(x)
pos = x > 0
tu = np.tanh(c * (x + 0.044715 * x**3))
du = c * (1 + 3 * 0.044715 * x**2)
d_gelu = 0.5 * (1 + tu) + 0.5 * x * (1 - tu**2) * du
```

## Common mistakes

- **`x >= 0` for the ReLU mask.** The derivative at exactly $0$ becomes $1$ instead of $0$. Leaky ReLU gets $1$ instead of $\alpha$.
- **Forgetting the product rule in GELU.** $\tfrac12(1+\tanh u)$ is only half the derivative. The $x \cdot \frac{d}{dx}\tanh u$ term matters for $|x|$ around $1$.
- **Plugging $x$ into $s(1-s)$.** The sigmoid derivative is written in terms of the output, not the input.
- **Naive `1 / (1 + np.exp(-x))`.** It still returns the right limit, but it raises overflow warnings for $x = -1000$.

## Complexity

- **Time:** $O(n)$ for $n$ elements, a constant number of passes.
- **Space:** $O(n)$ for each of the ten outputs.
