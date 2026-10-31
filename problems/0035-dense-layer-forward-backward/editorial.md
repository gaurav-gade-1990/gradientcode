## Approach

Treat every leading position as one row of a 2-D batch. Flatten `x` to `(R, D)` and `dout` to `(R, M)`, where `R` is the product of the leading dimensions. Then the layer is `out = X W + b` with a plain matrix product.

The rules come from the chain rule, and the shapes tell you where the transposes go:

$$
dX = dO\, W^\top \quad (R \times D), \qquad dW = X^\top dO \quad (D \times M), \qquad db = \textstyle\sum_r dO_{r,:} \quad (M)
$$

`W` and `b` are reused by every row, so their gradients **sum** over rows. That's the same thing as un-broadcasting `b`.

```python
out = x @ W + b
x2 = x.reshape(-1, D)
d2 = dout.reshape(-1, M)
dx = (d2 @ W.T).reshape(x.shape)
dW = x2.T @ d2
db = d2.sum(axis=0)
```

## Common mistakes

- **Writing it only for 2-D inputs.** `x.T` on a 3-D array reverses all three axes, so `x.T @ dout` is not $dW$. Flatten the leading dimensions first.
- **Averaging instead of summing for `db`.** If the loss is a mean, the $1/N$ is already inside `dout`. Dividing again scales the bias gradient wrongly.
- **`dout.T @ x` reshaped to `(D, M)`.** That has the right shape but the wrong layout. Transpose it, or better, write `x.T @ dout`.

## Complexity

- **Time:** $O(R D M)$ for the forward pass and for each of `dx` and `dW`.
- **Space:** $O(R(D + M) + DM)$ for the outputs.
