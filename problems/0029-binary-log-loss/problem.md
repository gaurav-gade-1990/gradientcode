Compute the **binary cross-entropy** (log loss) of predicted probabilities.

Given labels `y_true` in $\{0, 1\}$ and predicted probabilities `p` of the positive class, first **clip** the probabilities so the logs stay finite:

$$
\tilde p_i = \min\big(\max(p_i, \epsilon),\ 1 - \epsilon\big)
$$

then return the **mean** loss over the $n$ samples:

$$
\mathcal{L} = -\frac{1}{n} \sum_{i=1}^{n} \Big[ y_i \log \tilde p_i + (1 - y_i) \log (1 - \tilde p_i) \Big]
$$

`log` is the natural logarithm. Return a Python `float`.

**Constraints**

- `y_true` and `p` are 1-D arrays of the same length, `1 <= n <= 10^5`
- `y_true[i]` is `0` or `1`
- `0 <= p[i] <= 1`, and `p` may contain exact `0`s and `1`s
- `0 < eps < 0.5`
