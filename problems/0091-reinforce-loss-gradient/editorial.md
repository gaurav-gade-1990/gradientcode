## Approach

The policy-gradient theorem says $\nabla_\theta J = \mathbb{E}\bigl[\sum_t G_t \nabla_\theta \log\pi(a_t \mid s_t)\bigr]$. To train with autodiff, write a surrogate loss whose gradient is that estimate:

$$
L = -\frac{1}{T}\sum_t \hat G_t \log\pi(a_t \mid s_t)
$$

**Normalizing the returns** subtracts a baseline, the mean, which cuts the variance without biasing the gradient. It also divides by the std, which keeps the step size steady across episodes with very different reward scales.

For a softmax policy, the log-probability gradient has a simple closed form:

$$
\frac{\partial \log\operatorname{softmax}(z)_a}{\partial z} = e_a - \operatorname{softmax}(z)
\quad\Rightarrow\quad
\frac{\partial L}{\partial z_t} = \frac{\hat G_t}{T}\bigl(\pi_t - e_{a_t}\bigr)
$$

```python
G = np.zeros(T); running = 0.0
for t in range(T - 1, -1, -1):
    running = rewards[t] + gamma * running
    G[t] = running
G_hat = (G - G.mean()) / (G.std() + eps)

z = logits - logits.max(axis=1, keepdims=True)
log_probs = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
rows = np.arange(T)
loss = -np.mean(G_hat * log_probs[rows, actions])

grad = np.exp(log_probs)
grad[rows, actions] -= 1
grad *= G_hat[:, None] / T
```

When every return is equal, $\sigma = 0$ and $\hat G = 0 / \varepsilon = 0$, so nothing is learned from that episode. That's the right behavior: no action did better than average.

## Common mistakes

- **Sample std.** `np.std(ddof=1)` changes the scale. The spec uses the population std.
- **Naive softmax.** `np.exp(1000)` overflows and the loss becomes `nan`.
- **Accumulating returns forward.** $G_t$ sums **future** rewards, so the loop runs from the end.
- **Gradient sign.** The gradient of the *loss* is $\pi - e_a$. The gradient of the *objective* is $e_a - \pi$.

## Complexity

- **Time:** $O(TA)$.
- **Space:** $O(TA)$ for the log-probabilities and the gradient.
