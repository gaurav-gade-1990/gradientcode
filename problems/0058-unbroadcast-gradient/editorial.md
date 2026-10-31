## Approach

Broadcasting copies an element to many output positions. In the backward pass each copy sends a gradient back, and the copies' gradients **add up** (the multivariate chain rule). So unbroadcasting is a sum over every axis that was stretched.

NumPy aligns shapes from the right. That gives two kinds of stretched axis:

1. **Leading axes** that `x` didn't have. Sum them away completely.
2. **Size-1 axes** in `x` that are larger in `grad`. Sum them with `keepdims=True` so they stay as size 1.

Do the leading axes first. After that, `grad` and `shape` have the same rank and their axis numbers line up.

```python
def unbroadcast(grad, shape):
    extra = grad.ndim - len(shape)
    if extra > 0:
        grad = grad.sum(axis=tuple(range(extra)))
    axes = tuple(i for i, s in enumerate(shape) if s == 1 and grad.shape[i] != 1)
    if axes:
        grad = grad.sum(axis=axes, keepdims=True)
    return grad.reshape(shape)
```

The final `reshape` only matters for `shape == ()`, where the sum is already a 0-d value. This helper is used by every elementwise op in a tensor autograd engine, for example for the bias gradient in `x @ W + b`.

## Common mistakes

- **Only the leading axes.** A `(2, 1)` column broadcast across 3 columns comes back as `(2, 3)`.
- **Axis numbers off by the rank difference.** If you sum the size-1 axes before dropping the leading ones, `shape`'s axis `i` is `grad`'s axis `i + extra`.
- **Mean instead of sum.** Each copy contributes its full gradient. Averaging is only correct if the forward pass also averaged.

## Complexity

- **Time:** $O(N)$ for $N$ elements of `grad`.
- **Space:** $O(N)$ in the worst case for the intermediate sums. The output has `prod(shape)` elements.
