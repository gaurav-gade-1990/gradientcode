Implement the forward and backward pass of a **fully connected (dense) layer**.

The forward pass is

$$
\text{out} = x W + b
$$

where `x` has shape `(..., D)`, `W` has shape `(D, M)` and `b` has shape `(M,)`. The leading dimensions `...` can be anything: `(N,)` for a batch of vectors, or `(B, T)` for a batch of sequences. The matrix product acts on the last axis, and `b` broadcasts over every leading position.

You are also given `dout` $= \partial L / \partial\, \text{out}$, the upstream gradient of some scalar loss $L$, with the same shape as `out`. Compute

$$
dx = \frac{\partial L}{\partial x}, \qquad dW = \frac{\partial L}{\partial W}, \qquad db = \frac{\partial L}{\partial b}
$$

Since `W` and `b` are shared by every leading position, their gradients **sum** the contributions from all of them.

Return a tuple `(out, dx, dW, db)` with shapes `(..., M)`, `(..., D)`, `(D, M)` and `(M,)`.

**Constraints**

- `1 <= x.ndim <= 3`; when `x.ndim == 1` there are no leading dimensions and `out` has shape `(M,)`
- `1 <= D, M <= 64`
- All inputs are float arrays
