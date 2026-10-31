Compute the **mean softmax cross-entropy loss** and its gradient with respect to the logits.

You get `logits` $z$ of shape `(N, C)` and integer `labels` $y$ of shape `(N,)` with values in `[0, C)`. With $p_i = \operatorname{softmax}(z_i)$ taken over each row,

$$
L = -\frac{1}{N} \sum_{i=1}^{N} \log p_{i, y_i}
$$

Return a tuple `(loss, dlogits)`, where `loss` is a Python float and `dlogits` $= \partial L / \partial z$ has shape `(N, C)`.

The computation must be **numerically stable**. Logits can be as large as `±1e4` in magnitude, and the correct class can have a probability that underflows to `0.0` in float64. The loss must still be finite and correct in that case.

**Constraints**

- `1 <= N <= 200`, `2 <= C <= 50`
- `-1e4 <= logits <= 1e4`
- `labels` is an int array
