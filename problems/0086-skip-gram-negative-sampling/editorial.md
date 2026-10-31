## Approach

Negative sampling replaces the full softmax over the vocabulary with $K + 1$ binary logistic regressions: push the true context's score up, and push $K$ random words' scores down.

Let $s_o = u_o^\top v$ and $s_k = u_k^\top v$. Two scalar facts drive everything:

$$
\frac{d}{dx}\bigl[-\log\sigma(x)\bigr] = \sigma(x) - 1, \qquad \frac{d}{dx}\bigl[-\log\sigma(-x)\bigr] = \sigma(x)
$$

So the upstream gradients are $g_o = \sigma(s_o) - 1$ and $g_k = \sigma(s_k)$. The chain rule through the dot products gives

$$
\frac{\partial L}{\partial v} = g_o\,u_o + \sum_k g_k\,u_k, \qquad
\frac{\partial L}{\partial u_o} = g_o\,v, \qquad
\frac{\partial L}{\partial u_k} = g_k\,v
$$

### Stability

$-\log\sigma(x) = \log(1 + e^{-x})$ is `np.logaddexp(0, -x)`, which never overflows. The sigmoid itself is computed from $e^{-|x|}$, so it never overflows either.

### Bookkeeping

Negatives are sampled with replacement, so an index can repeat or even equal the context. Each occurrence is a separate term in the loss, and each adds to the same row. `dW_out[negatives] = ...` keeps only the last write for a repeated index. `np.add.at` accumulates.

```python
v, u_o, U_neg = W_in[center], W_out[context], W_out[negatives]
s_o, s_neg = u_o @ v, U_neg @ v
loss = np.logaddexp(0, -s_o) + np.sum(np.logaddexp(0, s_neg))
g_o, g_neg = _sigmoid(s_o) - 1, _sigmoid(s_neg)

dW_in = np.zeros_like(W_in)
dW_in[center] = g_o * u_o + g_neg @ U_neg
dW_out = np.zeros_like(W_out)
dW_out[context] += g_o * v
np.add.at(dW_out, negatives, g_neg[:, None] * v)
```

## Common mistakes

- **Assigning instead of accumulating.** Repeated negatives, or a negative equal to the context, lose gradient.
- **Naive `log(sigmoid(x))`.** With $x = -1000$, `sigmoid` rounds to `0` and the loss becomes `inf`.
- **Sign slip on negatives.** The negative terms use $\sigma(-s_k)$ in the loss, but their gradient is $+\sigma(s_k)$, not $\sigma(s_k) - 1$.
- **Forgetting the negatives in $\partial L / \partial v$.** The center vector gets gradient from all $K + 1$ terms.

## Complexity

- **Time:** $O(Kd)$ for the loss and the gradients, plus $O(Vd)$ to allocate dense gradient tables. Real implementations do sparse row updates instead, which is why word2vec is fast: each step touches only $K + 2$ rows, not $V$.
- **Space:** $O(Vd)$ for the dense outputs here, $O(Kd)$ in a sparse implementation.
