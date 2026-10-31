## Approach

Gradient descent on MSE is the residual, pushed back through the inputs. Let $r = Xw + b - y$. Differentiating $\frac{1}{n}\sum r_i^2$ gives

$$
\nabla_w L = \frac{2}{n} X^\top r, \qquad \frac{\partial L}{\partial b} = \frac{2}{n}\sum_i r_i .
$$

Both gradients come from the **same** residual, and then both parameters move together:

```python
def linear_regression_gd(X, y, lr, n_iters):
    n, d = X.shape
    w, b = np.zeros(d), 0.0
    for _ in range(n_iters):
        r = X @ w + b - y
        w = w - lr * (2.0 / n) * (X.T @ r)
        b = b - lr * (2.0 / n) * np.sum(r)
    return w, float(b)
```

Each iteration is fully vectorized. The only Python loop runs over iterations, and it can't be removed because each step depends on the previous one.

## Common mistakes

- **Dropping the 2.** The gradient of $\frac{1}{n}\sum r^2$ has a factor 2. Leaving it out halves the effective learning rate. That's equivalent to optimizing $\frac{1}{2n}\sum r^2$, which is a different loss from the one specified.
- **Updating `b` with the new `w`.** Recomputing the residual after updating `w` turns the step into coordinate descent. It still converges, but it follows a different path.
- **Summing instead of averaging.** The step then scales with $n$, and a learning rate that is fine for 10 samples diverges for 1000.

## Complexity

- **Time:** $O(T\, n d)$ for $T$ iterations.
- **Space:** $O(n + d)$ beyond the input.
