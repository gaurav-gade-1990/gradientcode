## Approach: shift by the max

Softmax doesn't change if you add the same constant to every input on a slice:

$$
\frac{e^{x_i - c}}{\sum_j e^{x_j - c}} = \frac{e^{-c} e^{x_i}}{e^{-c} \sum_j e^{x_j}}
$$

Choose $c = \max_j x_j$. The largest exponent is then $e^0 = 1$, so the numerator can't overflow. The denominator is at least $1$, so it can't underflow to zero.

```python
def softmax(x, axis=-1):
    z = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(z)
    return e / np.sum(e, axis=axis, keepdims=True)
```

`keepdims=True` matters. It keeps the reduced axis as size 1, so the max and the sum broadcast back against `x` for any `axis`.

## Common mistakes

- **No shift.** `np.exp(1000)` is `inf`, and `inf / inf` is `nan`.
- **Global max.** `np.max(x)` without an axis still gives the right answer mathematically. It can underflow, though: a row whose values sit far below the global max becomes all zeros, and `0 / 0` is `nan`.
- **Missing `keepdims`.** The division broadcasts along the wrong axis.

## Complexity

- **Time:** $O(n)$ for $n$ elements. There are three passes: max, exp and sum.
- **Space:** $O(n)$ for the output.
