Cut a 1-D signal `x` of length `n` into overlapping (or strided) **windows**.

Window `k` starts at index `k * stride` and holds `window` consecutive samples:

$$
W_{k, t} = x[k \cdot \text{stride} + t], \qquad 0 \le t < \text{window}
$$

Keep only **full** windows: a window is included only if it ends inside the signal, `k * stride + window <= n`. There is no padding and no partial window at the end. So the number of windows is

$$
\text{num\_windows} = \begin{cases} \left\lfloor \dfrac{n - \text{window}}{\text{stride}} \right\rfloor + 1 & n \ge \text{window} \\ 0 & n < \text{window} \end{cases}
$$

Return an array of shape `(num_windows, window)` with the same dtype as `x`. When there are no windows, return shape `(0, window)`. Build it without a Python loop over windows (fancy indexing or `np.lib.stride_tricks` are both fine). The result must be a fresh array, not a view the caller could write through.

This is the 1-D version of the `im2col` trick that turns a convolution into a matrix product.

**Constraints**

- `x` is a 1-D array (integer or float), `0 <= n <= 10^5`
- `1 <= window <= 1000`
- `1 <= stride <= 1000`
