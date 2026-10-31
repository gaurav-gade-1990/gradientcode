## Approach: center, solve, recover the bias

For any fixed $w$, the best bias is $b = \bar y - \bar x^\top w$, because the bias isn't penalized. Substituting it back gives a ridge problem on **centered** data, where the bias is gone:

$$
\min_w \lVert X_c w - y_c \rVert^2 + \alpha \lVert w \rVert^2
\quad\Longrightarrow\quad
(X_c^\top X_c + \alpha I)\, w = X_c^\top y_c .
$$

$X_c^\top X_c$ is positive semi-definite, so adding $\alpha I$ with $\alpha > 0$ makes the system positive definite. It has a unique solution even when the columns are collinear or $n < d$.

```python
def ridge_regression(X, y, alpha):
    x_mean, y_mean = X.mean(axis=0), y.mean()
    Xc, yc = X - x_mean, y - y_mean
    w = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(X.shape[1]), Xc.T @ yc)
    return w, float(y_mean - x_mean @ w)
```

An equivalent approach augments $X$ with a ones column and uses the penalty matrix $\operatorname{diag}(\alpha, \dots, \alpha, 0)$, with a zero in the bias slot.

## Common mistakes

- **Penalizing the bias.** Adding $\alpha I$ to the full augmented system shrinks $b$ toward 0. Predictions then depend on where the origin of $y$ happens to be.
- **Forgetting to recover $b$.** $b = \bar y$ is right only when the features have mean zero.
- **Using `inv`.** Use `solve`. It's faster and more accurate.

## Complexity

- **Time:** $O(n d^2 + d^3)$ to form $X_c^\top X_c$ and solve.
- **Space:** $O(n d + d^2)$.
