Given two sets of vectors, `A` with shape `(n, d)` and `B` with shape `(m, d)`, return the `(n, m)` matrix of **cosine similarities**:

$$
S_{ij} = \frac{a_i \cdot b_j}{\lVert a_i \rVert_2 \, \lVert b_j \rVert_2}
$$

where $a_i$ is row `i` of `A` and $b_j$ is row `j` of `B`.

If either $a_i$ or $b_j$ is the zero vector, define $S_{ij} = 0$. Your output must not contain `nan` or `inf`.

Vectorize it: no Python loops over rows.

**Constraints**

- `A` and `B` are float arrays with the same number of columns `d >= 1`
- `1 <= n, m <= 500`
- rows may be all zeros
