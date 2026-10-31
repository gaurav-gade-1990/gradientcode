## Approach

The forward pass is two dense layers with a `tanh` between them and a sigmoid on top. The backward pass reads the same graph in reverse.

The sigmoid and the cross-entropy cancel. For the mean loss over $N$ rows, the gradient with respect to the logit is

$$
\frac{\partial L}{\partial z_i} = \frac{p_i - y_i}{N}
$$

From there each layer is the dense-layer rule, and `tanh` contributes $1 - h^2$:

$$
\begin{aligned}
dW_2 &= h^\top dz, & db_2 &= \textstyle\sum_i dz_i \\
dh &= dz\, W_2^\top, & da &= dh \odot (1 - h^2) \\
dW_1 &= X^\top da, & db_1 &= \textstyle\sum_i da_i
\end{aligned}
$$

```python
for t in range(epochs):
    h = np.tanh(X @ W1 + b1)
    z = (h @ W2 + b2)[:, 0]
    losses[t] = np.mean(np.logaddexp(0, z) - y * z)     # = BCE, stable
    p = 1 / (1 + np.exp(-z))
    dz = ((p - y) / N)[:, None]
    dW2, db2 = h.T @ dz, dz.sum(0)
    da = (dz @ W2.T) * (1 - h**2)
    dW1, db1 = X.T @ da, da.sum(0)
    W1 -= lr * dW1; b1 -= lr * db1; W2 -= lr * dW2; b2 -= lr * db2
```

$\log(1 + e^z) - yz$ is the cross-entropy written in terms of the logit. It equals the formula in the statement, and it can't produce `log(0)`.

Copy the parameters before the loop. In-place `-=` would otherwise modify the caller's arrays.

## Common mistakes

- **Updating `W2` before backpropagating through it.** `dh` must use the `W2` that produced the forward pass. Interleaving updates and backprop gives a different (and wrong) gradient for the first layer.
- **Forgetting the `tanh` derivative.** Without $(1 - h^2)$ the first layer trains as if the hidden units were linear.
- **Dropping the $1/N$.** The loss is a mean. The gradient of the sum is $N$ times larger, which acts like a larger learning rate.
- **Recording the loss after the update.** It shifts the curve by one step, and `losses[0]` should be the loss at the initial weights.

## Complexity

- **Time:** $O(\text{epochs} \cdot N H)$. Each iteration is a handful of tiny matrix products.
- **Space:** $O(NH)$ for the activations, plus $O(\text{epochs})$ for the loss history.
