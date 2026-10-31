For each row of a 2-D array `x` with shape `(n, m)`, find the `k` **largest** entries.

Return a tuple `(values, indices)`:

- `indices` is an integer array of shape `(n, k)`. Row `i` lists the column indices of the `k` largest entries of `x[i]`, ordered from largest value to smallest.
- `values` has shape `(n, k)` and the same dtype as `x`, with `values[i, j] = x[i, indices[i, j]]`.

**Ties:** among equal values, the lower column index comes first. That rule fixes both which entries make the cut and their order, so the answer is unique.

**Constraints**

- `x` is a 2-D float array with `1 <= n <= 1000`, `1 <= m <= 1000`, and no `nan`
- `1 <= k <= m`
