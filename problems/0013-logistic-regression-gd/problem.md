Train a binary **logistic regression** classifier with full-batch gradient descent on the mean binary cross-entropy

$$
L(w, b) = -\frac{1}{n} \sum_{i=1}^{n} \Big[ y_i \log p_i + (1 - y_i) \log (1 - p_i) \Big], \qquad p_i = \sigma(x_i^\top w + b),
$$

where $\sigma(z) = 1 / (1 + e^{-z})$.

Start from $w = \mathbf{0}$ and $b = 0$, and run exactly `n_iters` iterations. Each iteration:

1. computes $p = \sigma(Xw + b)$ with the current parameters,
2. computes the gradients $\nabla_w L = \frac{1}{n} X^\top (p - y)$ and $\partial L/\partial b = \frac{1}{n} \sum_i (p_i - y_i)$,
3. updates both parameters at once: $w \leftarrow w - \eta \nabla_w L$ and $b \leftarrow b - \eta\, \partial L/\partial b$.

Your sigmoid must be **numerically stable**. Features can be large, so the logits can reach $\pm 10^5$. The result must contain no `nan`.

Return a tuple `(w, b)`: `w` is a float array of shape `(d,)` and `b` is a Python float.

**Constraints**

- `1 <= n <= 200`, `1 <= d <= 8`
- `y[i]` is `0.0` or `1.0`
- `0 <= n_iters <= 2000`, `lr > 0`
