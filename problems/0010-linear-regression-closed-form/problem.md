Fit an **ordinary least-squares** linear regression with an intercept.

Given a design matrix `X` of shape `(n, d)` and targets `y` of shape `(n,)`, find the weights $w \in \mathbb{R}^d$ and bias $b \in \mathbb{R}$ that minimize the squared error

$$
L(w, b) = \sum_{i=1}^{n} \left( x_i^\top w + b - y_i \right)^2 .
$$

Append a column of ones to `X` to get $A = [X \;\; \mathbf{1}]$, and solve for $\theta = [w; b]$ in the least-squares sense.

If the columns of $A$ are linearly dependent, many $\theta$ minimize $L$. Return the one with the **smallest norm** $\lVert \theta \rVert_2$ (the norm covers $w$ and $b$ together). This is what `np.linalg.lstsq` and `np.linalg.pinv` return.

Return a tuple `(w, b)`: `w` is a float array of shape `(d,)` and `b` is a Python float.

**Constraints**

- `1 <= n <= 200`, `1 <= d <= 10`
- `X` and `y` are float arrays
- `n` may be smaller than `d + 1`, and columns may be duplicated
