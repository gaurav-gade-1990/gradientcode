## Approach: normalize, then one matmul

Cosine similarity is the dot product of two unit vectors. Normalize every row once, and a single matrix product gives every pair:

$$
\hat a_i = \frac{a_i}{\lVert a_i \rVert}, \quad \hat b_j = \frac{b_j}{\lVert b_j \rVert}, \quad S = \hat A \hat B^\top
$$

A zero row has norm `0`. Dividing it by `1` instead leaves it a zero vector, and every dot product with a zero vector is `0`, which is exactly the rule.

```python
def cosine_similarity(A, B):
    na = np.linalg.norm(A, axis=1, keepdims=True)
    nb = np.linalg.norm(B, axis=1, keepdims=True)
    A_unit = A / np.where(na == 0, 1.0, na)
    B_unit = B / np.where(nb == 0, 1.0, nb)
    return A_unit @ B_unit.T
```

## Common mistakes

- **No zero guard.** `0 / 0` is `nan`. Adding a tiny `eps` to the denominator also works, but the `where` keeps nonzero rows exact.
- **Norm over the wrong axis.** `axis=0` normalizes the columns (features), not the vectors. The result has the right shape and wrong values.
- **Missing `keepdims`.** An `(n,)` norm broadcasts against `(n, d)` along the last axis, which divides column `j` by the norm of row `j`.

## Complexity

- **Time:** $O(nmd)$ for the matrix product, plus $O((n + m)d)$ for the norms.
- **Space:** $O(nm)$ for the output.
