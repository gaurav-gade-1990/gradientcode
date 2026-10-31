## Approach

The hinge loss $\max(0, 1 - m)$ isn't differentiable at $m = 1$, so use a **subgradient**: $-y_i x_i$ when the margin is below 1, and $0$ otherwise. Add the gradient of the L2 term, which covers $w$ only:

$$
g_w = \lambda w - \frac{1}{n}\sum_{m_i < 1} y_i x_i, \qquad g_b = -\frac{1}{n}\sum_{m_i < 1} y_i .
$$

Pegasos uses $\eta_t = 1/(\lambda t)$. The objective is $\lambda$-strongly convex in $w$, and this schedule gives an $O(1/t)$ rate. Note that the first step, $\eta_1 = 1/\lambda$, exactly cancels the $\lambda w$ term: $w - \eta_1 \lambda w = 0$.

```python
def linear_svm(X, y, lam, n_iters):
    n, d = X.shape
    w, b = np.zeros(d), 0.0
    for t in range(1, n_iters + 1):
        ya = y * (y * (X @ w + b) < 1)          # y_i on active samples, 0 elsewhere
        g_w = lam * w - (ya @ X) / n
        g_b = -ya.sum() / n
        eta = 1.0 / (lam * t)
        w, b = w - eta * g_w, b - eta * g_b
    return w, float(b)
```

## Common mistakes

- **Regularizing the bias.** A $\lambda b$ term pulls the decision boundary toward the origin. It hurts most on imbalanced data.
- **Averaging over the active set.** The loss averages over all $n$ samples. Dividing by $|\mathcal{A}|$ inflates the step whenever few samples are active.
- **Off-by-one in the schedule.** Starting the step counter at $t = 0$ divides by zero. Shifting it to $t + 1$ to avoid that changes every step.

## Complexity

- **Time:** $O(T\, n d)$.
- **Space:** $O(n + d)$.
