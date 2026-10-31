## Approach: expand the square

The double loop does $nm$ small vector operations in Python. Expanding the square turns it into one matrix product, which NumPy hands to BLAS:

$$
D^2_{ij} = \lVert a_i \rVert^2 - 2\, a_i \cdot b_j + \lVert b_j \rVert^2
$$

- $\lVert a_i \rVert^2$ for every row is `np.sum(A * A, axis=1)`, shaped as a column `(n, 1)`.
- $\lVert b_j \rVert^2$ is a row `(1, m)`.
- All the cross terms at once are `A @ B.T`, shape `(n, m)`.

Broadcasting the column plus the row gives the full `(n, m)` grid.

```python
def pairwise_distances(A, B):
    aa = np.sum(A * A, axis=1)[:, None]
    bb = np.sum(B * B, axis=1)[None, :]
    d2 = aa - 2.0 * (A @ B.T) + bb
    return np.sqrt(np.maximum(d2, 0.0))
```

### Why clip?

For two equal points the exact answer is $0$, but the formula subtracts large, nearly equal numbers. The rounding error can land on either side of zero, and `np.sqrt(-1e-14)` is `nan`. Clipping at `0` fixes it. The leftover error is about $\sqrt{\varepsilon \lVert a \rVert^2}$, which is why distances computed this way aren't exact on the diagonal. scikit-learn makes the same trade.

## Common mistakes

- **No clip.** One `nan` on the diagonal when `A` and `B` share points.
- **Returning squared distances.** Fine for nearest-neighbor ranking, but the problem asks for distances.
- **Broadcasting the difference.** `A[:, None, :] - B[None, :, :]` is correct but builds an `(n, m, d)` temporary. At `1000 x 1000 x 32` that is 256 MB.
- **Python loops.** Correct and about 500 times slower.

## Complexity

- **Time:** $O(nmd)$, all inside one matrix product.
- **Space:** $O(nm)$ for the output. Nothing of size $nmd$ is built.
