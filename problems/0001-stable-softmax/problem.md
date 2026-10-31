Implement the **softmax** function along a given axis of an array.

$$
\operatorname{softmax}(x)_i = \frac{e^{x_i}}{\sum_j e^{x_j}}
$$

Your implementation must be **numerically stable**. Inputs can contain values like `1000` or `-1000`. A naive `np.exp(x)` overflows to `inf` on them and produces `nan`.

Return an array with the same shape as `x`. Every slice along `axis` must be non-negative and sum to `1`.

**Constraints**

- `x` is a float array with `1 <= x.ndim <= 3`
- `-1e4 <= x[i] <= 1e4`
- `axis` is a valid axis for `x` (it may be negative)
