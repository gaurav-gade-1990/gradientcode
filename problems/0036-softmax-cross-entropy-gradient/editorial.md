## Approach

Work in log space. For a row $z$ with max $m$,

$$
\log p_k = z_k - \log \sum_j e^{z_j} = (z_k - m) - \log \sum_j e^{z_j - m}
$$

After the shift every exponent is at most $0$, and the sum is at least $1$. So the log never sees $0$ and nothing overflows. The loss is the mean of $-\log p_{i,y_i}$.

The gradient is the famous one. Softmax and cross-entropy cancel into

$$
\frac{\partial L}{\partial z_{ik}} = \frac{1}{N}\,(p_{ik} - [k = y_i])
$$

```python
z = logits - logits.max(axis=1, keepdims=True)
log_p = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
loss = -log_p[np.arange(N), labels].mean()
d = np.exp(log_p)
d[np.arange(N), labels] -= 1
d /= N
```

## Common mistakes

- **`np.log(softmax(z))`.** When the true class sits $1000$ below the max, its probability underflows to `0.0` and the loss becomes `inf`. Subtracting the log-sum-exp keeps it exact.
- **No max shift.** `np.exp(1000)` is `inf`, and the probabilities become `nan`.
- **Forgetting the $1/N$ in the gradient.** The loss is a mean, so the gradient is too. Without it, `dlogits` is $N$ times too large.

## Complexity

- **Time:** $O(NC)$.
- **Space:** $O(NC)$ for the log-probabilities and the gradient.
