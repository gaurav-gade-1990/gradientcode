Use **power iteration** to estimate the dominant eigenpair of a symmetric matrix $A$. The dominant eigenvalue is the one with the largest absolute value.

Start from $v = v_0 / \lVert v_0 \rVert_2$. Then repeat exactly `n_iters` times:

$$
w = A v, \qquad v = \frac{w}{\lVert w \rVert_2}.
$$

After the loop, estimate the eigenvalue with the **Rayleigh quotient** $\lambda = v^\top A v$.

Return a tuple `(eigenvalue, eigenvector)`: `eigenvalue` is a Python float, and `eigenvector` is the final unit vector $v$, a float array of shape `(d,)`.

An eigenvector is only defined up to sign. The judge accepts either $v$ or $-v$. The eigenvalue must match.

**Constraints**

- `A` is a symmetric float array of shape `(d, d)`, with `1 <= d <= 20`
- `0 <= n_iters <= 1000`
- $A v \ne 0$ at every step, and `v0` is not the zero vector
- Entries of `A` can be large, up to `1e3` in absolute value
