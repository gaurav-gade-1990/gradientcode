Train a linear regression model $\hat y = Xw + b$ with **full-batch gradient descent** on the mean squared error

$$
L(w, b) = \frac{1}{n} \sum_{i=1}^{n} \left( x_i^\top w + b - y_i \right)^2 .
$$

Start from $w = \mathbf{0}$ and $b = 0$. Then run exactly `n_iters` iterations. Each iteration:

1. computes the residual $r = Xw + b - y$ with the current parameters,
2. computes both gradients from that residual,
$$
\nabla_w L = \frac{2}{n} X^\top r, \qquad \frac{\partial L}{\partial b} = \frac{2}{n} \sum_i r_i ,
$$
3. updates both parameters at once: $w \leftarrow w - \eta\, \nabla_w L$ and $b \leftarrow b - \eta\, \partial L / \partial b$.

Return a tuple `(w, b)`: `w` is a float array of shape `(d,)` and `b` is a Python float.

**Constraints**

- `1 <= n <= 200`, `1 <= d <= 8`
- `0 <= n_iters <= 2000`
- `lr > 0`. It may be large enough to diverge; return whatever the updates produce.
