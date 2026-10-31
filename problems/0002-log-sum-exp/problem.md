Implement **log-sum-exp** along a given axis of an array.

$$
\operatorname{LSE}(x) = \log \sum_j e^{x_j}
$$

It shows up everywhere probabilities live in log space: the softmax denominator, the cross-entropy loss, and the log-likelihood of a mixture model.

Your implementation must be **numerically stable**. Inputs can be as large as `1e4` or as small as `-1e4`. A naive `np.exp(x)` overflows to `inf` for large values, and underflows to `0` (giving `log(0) = -inf`) for very negative ones.

Return the result with `axis` **removed** (like `keepdims=False`). For a 1-D input the result is a scalar.

**Constraints**

- `x` is a float array with `1 <= x.ndim <= 3` and at least one element along `axis`
- every entry is finite, `-1e4 <= x[i] <= 1e4`
- `axis` is a valid axis for `x` (it may be negative)
