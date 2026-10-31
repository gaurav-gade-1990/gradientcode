Train the classic **Rosenblatt perceptron** with online updates.

Labels are $y_i \in \{-1, +1\}$. Start from $w = \mathbf{0}$ and $b = 0$. Run `n_epochs` passes over the data. In each pass, visit the samples **in the given order** $i = 0, 1, \dots, n-1$, and for each one:

- if $y_i\,(w^\top x_i + b) \le 0$ (a mistake; a score of exactly zero counts as a mistake), update **immediately**
$$
w \leftarrow w + \eta\, y_i x_i, \qquad b \leftarrow b + \eta\, y_i ,
$$
- otherwise leave $w$ and $b$ unchanged.

Run all `n_epochs` passes. Don't stop early, although on separable data the later passes may change nothing.

Return a tuple `(w, b)`: `w` is a float array of shape `(d,)` and `b` is a Python float.

**Constraints**

- `1 <= n <= 100`, `1 <= d <= 6`
- `y[i]` is `-1.0` or `1.0`
- `0 <= n_epochs <= 50`, `lr > 0`
