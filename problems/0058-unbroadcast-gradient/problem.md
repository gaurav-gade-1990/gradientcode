In the forward pass, an input `x` with shape `shape` was **broadcast** against other arrays, so the output (and its upstream gradient `grad`) has a larger shape. Each element of `x` was reused at every position it was stretched over, so its gradient is the **sum** of `grad` over those positions.

Implement `unbroadcast(grad, shape)`. It returns the gradient with respect to `x`: an array with shape exactly `shape`.

Formally, if `y = np.broadcast_to(x, grad.shape)`, return $\partial L / \partial x$ given $\partial L / \partial y = $ `grad`. NumPy's broadcasting rules apply:

- Shapes are aligned from the **right**. If `shape` has fewer dimensions, the missing leading dimensions were added and must be summed away.
- Any aligned dimension where `shape` has size `1` and `grad` has size `k > 1` was stretched. Sum over it and keep it as size `1`.
- `shape` can be `()`, a scalar. Then return the sum of all of `grad` as a 0-d array.

Return a float array with `.shape == shape`.

**Constraints**

- `grad` is a float array with `0 <= grad.ndim <= 5`
- `shape` is a tuple of ints that broadcasts to `grad.shape`, so `np.broadcast_to(np.zeros(shape), grad.shape)` is valid
