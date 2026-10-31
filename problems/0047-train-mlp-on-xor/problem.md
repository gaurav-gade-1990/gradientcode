Train a **two-layer neural network** with full-batch gradient descent. The classic target is XOR, which no linear model can fit.

The network maps `X` of shape `(N, 2)` to a probability per row:

$$
h = \tanh(X W_1 + b_1), \qquad z = h W_2 + b_2, \qquad p = \sigma(z)
$$

with `W1` of shape `(2, H)`, `b1` of shape `(H,)`, `W2` of shape `(H, 1)` and `b2` of shape `(1,)`. The labels `y` have shape `(N,)` with values in $\{0, 1\}$. The loss is the mean binary cross-entropy:

$$
L = -\frac{1}{N}\sum_{i=1}^{N} \Big[ y_i \log p_i + (1 - y_i)\log(1 - p_i) \Big]
$$

Run exactly `epochs` iterations. In each one:

1. Run the forward pass with the current parameters and record $L$.
2. Backpropagate to get $\partial L/\partial W_1$, $\partial L/\partial b_1$, $\partial L/\partial W_2$ and $\partial L/\partial b_2$, all from the **current** parameters.
3. Update every parameter at once: $\theta \leftarrow \theta - \text{lr} \cdot \partial L / \partial \theta$.

After the last update, run one more forward pass.

Return a tuple `(losses, probs)`:

- `losses`: float array of shape `(epochs,)`. `losses[t]` is the loss recorded at the start of iteration `t`, before its update.
- `probs`: float array of shape `(N,)`, the probabilities $p$ from the final forward pass.

Don't modify the input arrays in place.

**Constraints**

- `1 <= N <= 16`, `1 <= H <= 8`, `1 <= epochs <= 2000`, `0 < lr <= 2`
- The inputs keep $p$ strictly inside $(0, 1)$ in float64, so the loss stays finite
