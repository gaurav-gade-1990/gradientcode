Implement **inverted dropout**.

During training, each element of `x` is kept with probability `keep_prob` and zeroed otherwise. Kept elements are scaled by $1 / \text{keep\_prob}$, so the expected value of each output equals its input and no rescaling is needed at test time.

The random numbers are passed in. `u` has the same shape as `x`, with entries in $[0, 1)$. Build the mask with

$$
\text{mask} = (u < \text{keep\_prob})
$$

using strict less-than, and return

$$
\text{out} = \frac{x \odot \text{mask}}{\text{keep\_prob}}
$$

When `train` is `False`, ignore `u` and return `x` unchanged (as a float array of the same shape).

**Constraints**

- `x` and `u` are float arrays of the same shape, with `0 <= u < 1`
- `0 < keep_prob <= 1`
