Fit **ridge regression** (L2-regularized least squares) in closed form. Find $w \in \mathbb{R}^d$ and $b \in \mathbb{R}$ that minimize

$$
L(w, b) = \sum_{i=1}^{n} \left( x_i^\top w + b - y_i \right)^2 + \alpha \lVert w \rVert_2^2 .
$$

The **bias is not regularized**. Only $w$ appears in the penalty, so shifting every target by a constant shifts $b$ by that constant and leaves $w$ unchanged.

Note that the loss is a **sum** over samples, not a mean. Don't rescale `alpha` by `n`.

Return a tuple `(w, b)`: `w` is a float array of shape `(d,)` and `b` is a Python float.

**Constraints**

- `1 <= n <= 200`, `1 <= d <= 10`
- `alpha > 0`
- Columns of `X` may be duplicated or constant, and `n` may be smaller than `d`. With `alpha > 0` the minimizer is still unique.
