## Approach

The sigmoid and the cross-entropy cancel nicely. With $z = Xw + b$,

$$
\frac{\partial L}{\partial z_i} = \frac{p_i - y_i}{n},
\qquad
\nabla_w L = \frac{1}{n} X^\top (p - y),
\qquad
\frac{\partial L}{\partial b} = \frac{1}{n} \sum_i (p_i - y_i).
$$

That has the same shape as the linear-regression gradient, with $p$ in place of $\hat y$ and no factor of 2.

### A stable sigmoid

$e^{-z}$ overflows for very negative $z$, and $e^{z}$ overflows for very positive $z$. Only ever exponentiate $-|z| \le 0$:

$$
\sigma(z) = \begin{cases} \dfrac{1}{1 + e^{-|z|}} & z \ge 0 \\[2mm] \dfrac{e^{-|z|}}{1 + e^{-|z|}} & z < 0 \end{cases}
$$

```python
def sigmoid(z):
    e = np.exp(-np.abs(z))
    return np.where(z >= 0, 1.0 / (1.0 + e), e / (1.0 + e))

def logistic_regression_gd(X, y, lr, n_iters):
    n, d = X.shape
    w, b = np.zeros(d), 0.0
    for _ in range(n_iters):
        g = sigmoid(X @ w + b) - y
        w = w - lr * X.T @ g / n
        b = b - lr * np.mean(g)
    return w, float(b)
```

## Common mistakes

- **`exp(z) / (1 + exp(z))`.** It's correct on paper, but for $z \gtrsim 710$ it evaluates `inf / inf = nan`, and the `nan` spreads into every weight.
- **Summing the gradient.** The loss is a mean, so divide by $n$. Otherwise the step scales with the dataset size.
- **Sign flip.** The gradient is $p - y$, not $y - p$. With the wrong sign, the loss goes up.

## Complexity

- **Time:** $O(T\, n d)$ for $T$ iterations.
- **Space:** $O(n + d)$.
