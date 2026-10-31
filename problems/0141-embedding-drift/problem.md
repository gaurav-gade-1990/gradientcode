Your support assistant routes tickets with an embedding model, and last quarter a product launch flooded it with a topic it had never seen. Write the nightly job that compares this week's ticket embeddings with the reference window and says whether they drifted.

`embedding_drift(ref, cur, cos_threshold, mmd_threshold)` gets two float arrays: `ref` with shape `(n, d)` and `cur` with shape `(m, d)`, one row per ticket. The judge builds them from ticket text with `gc_runtime.embed(text, dim=32)`. Return a dict with exactly these keys:

| key | value |
|---|---|
| `centroid_cosine_distance` | $1 - \dfrac{\mu_r \cdot \mu_c}{\lVert\mu_r\rVert\,\lVert\mu_c\rVert}$ with $\mu_r, \mu_c$ the row means. If either centroid has norm 0, use `1.0`. |
| `sigma` | The RBF bandwidth by the **median heuristic**: stack `ref` and `cur` into $Z$ ($n + m$ rows), take the Euclidean distance $\lVert z_i - z_j\rVert$ for every unordered pair $i < j$ (each pair once, no self-pairs), and return the median (the mean of the two middle values for an even count). If that median is 0, use `1.0`. |
| `mmd2` | The **unbiased** squared MMD with kernel $k(x, y) = \exp\!\left(-\lVert x - y\rVert^2 / (2\sigma^2)\right)$, given below. It can be slightly negative; return it as is. |
| `drifted` | `True` when `reasons` is non-empty. |
| `reasons` | A list: `"centroid_shift"` if `centroid_cosine_distance > cos_threshold`, then `"mmd"` if `mmd2 > mmd_threshold` (strict, in that order). |

$$
\widehat{\text{MMD}}^2 = \frac{1}{n(n-1)}\sum_{i \ne j} k(x_i, x_j) + \frac{1}{m(m-1)}\sum_{i \ne j} k(y_i, y_j) - \frac{2}{nm}\sum_{i, j} k(x_i, y_j)
$$

Return Python floats and a bool (NumPy scalars are fine).

**Constraints**

- `2 <= n, m <= 60`, `d = 32`
- Rows are L2-normalized embeddings, or all zeros for an empty ticket body
- Compared with relative tolerance `1e-6`
