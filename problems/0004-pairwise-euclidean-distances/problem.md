Given `A` with shape `(n, d)` and `B` with shape `(m, d)`, return the `(n, m)` matrix of **Euclidean distances** between every row of `A` and every row of `B`:

$$
D_{ij} = \lVert a_i - b_j \rVert_2
$$

This is the inner loop of k-nearest neighbors and k-means, so it has to be fast. **Vectorize it** with the expansion

$$
\lVert a - b \rVert^2 = \lVert a \rVert^2 - 2\, a \cdot b + \lVert b \rVert^2
$$

The cross term for all pairs is a single matrix product. Floating-point cancellation can make a squared distance come out slightly **negative** when two points are (nearly) equal, so **clip the squared distances at `0`** before taking the square root. The output must not contain `nan`.

One hidden test uses `n = m = 1000`, `d = 32` with a tight time limit. A double Python loop over pairs will time out.

**Constraints**

- `A` and `B` are float arrays with the same number of columns, `1 <= d <= 64`
- `1 <= n, m <= 1000`
- entries satisfy `|x| <= 10`
- answers are checked with `atol = 1e-5`, so clipped rounding noise on equal points is fine
