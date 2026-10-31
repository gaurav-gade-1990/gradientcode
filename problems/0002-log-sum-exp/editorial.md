## Approach: factor out the max

Pull a constant $c$ out of every exponential:

$$
\log \sum_j e^{x_j} = \log\Big(e^{c} \sum_j e^{x_j - c}\Big) = c + \log \sum_j e^{x_j - c}
$$

Choose $c = \max_j x_j$. Every shifted exponent is $\le 0$, so nothing overflows, and the largest term is exactly $e^0 = 1$, so the sum is at least $1$ and the log can't be $-\infty$.

```python
def logsumexp(x, axis=-1):
    c = np.max(x, axis=axis, keepdims=True)
    s = np.log(np.sum(np.exp(x - c), axis=axis, keepdims=True)) + c
    return np.squeeze(s, axis=axis)
```

Keep the reduced axis while you compute, so `c` broadcasts against `x` for any `axis`, then squeeze it at the end.

## Common mistakes

- **No shift.** `np.exp(1000)` is `inf`, and for very negative rows every term underflows to `0`, so the log is `-inf`.
- **Global max.** Shifting by `np.max(x)` over the whole array protects the largest row but not a row that sits far below it. Its terms all underflow to `0`.
- **Leaving `keepdims=True` on the output.** The answer has the reduced axis removed. A `(4, 1)` result where `(4,)` was expected is a shape mismatch.

## Complexity

- **Time:** $O(n)$ for $n$ elements: a max, an exp and a sum.
- **Space:** $O(n)$ for the shifted temporary.
