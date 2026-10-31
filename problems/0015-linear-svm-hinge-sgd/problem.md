Train a soft-margin **linear SVM** by full-batch subgradient descent with the Pegasos step-size schedule. The objective is

$$
f(w, b) = \frac{\lambda}{2} \lVert w \rVert^2 + \frac{1}{n} \sum_{i=1}^{n} \max\!\big(0,\; 1 - y_i (w^\top x_i + b)\big),
$$

with labels $y_i \in \{-1, +1\}$. The bias $b$ is **not** regularized.

Start from $w = \mathbf{0}$ and $b = 0$. For $t = 1, 2, \dots, T$ (`T = n_iters`):

1. Compute the margins $m_i = y_i (w^\top x_i + b)$ with the current parameters. The active set is $\mathcal{A} = \{ i : m_i < 1 \}$ (strict).
2. Compute the subgradient
$$
g_w = \lambda w - \frac{1}{n} \sum_{i \in \mathcal{A}} y_i x_i, \qquad g_b = -\frac{1}{n} \sum_{i \in \mathcal{A}} y_i .
$$
3. Set $\eta_t = \dfrac{1}{\lambda t}$ and update both at once: $w \leftarrow w - \eta_t g_w$ and $b \leftarrow b - \eta_t g_b$.

Return a tuple `(w, b)`: `w` is a float array of shape `(d,)` and `b` is a Python float.

**Constraints**

- `1 <= n <= 200`, `1 <= d <= 8`
- `y[i]` is `-1.0` or `1.0`
- `lam > 0`, `0 <= n_iters <= 1000`
