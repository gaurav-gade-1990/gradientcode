Compute the **REINFORCE** policy-gradient loss (Williams, 1992) for one episode, and its gradient with respect to the policy's logits.

At step $t$ the policy is $\pi(\cdot \mid s_t) = \operatorname{softmax}(z_t)$, where $z_t$ = `logits[t]`. The agent took action $a_t$ = `actions[t]` and got reward $r_t$ = `rewards[t]`.

1. **Discounted returns:** $G_t = \sum_{k=t}^{T-1}\gamma^{k-t} r_k$.
2. **Normalized returns** (a baseline that also rescales): $\hat G_t = \dfrac{G_t - \mu}{\sigma + \varepsilon}$, where $\mu$ and $\sigma$ are the mean and the **population** standard deviation (`ddof=0`) of $G$ over the episode.
3. **Loss:**

$$
L = -\frac{1}{T}\sum_{t=0}^{T-1}\hat G_t \log\pi(a_t \mid s_t)
$$

4. **Gradient:** $\partial L / \partial z_t$, treating $\hat G$ as a constant (no gradient flows through the returns).

Return a tuple `(loss, grad)`: `loss` is a Python float and `grad` is a float array of shape `(T, A)`.

Logits can be large (up to `1e3` in magnitude), so compute log-probabilities stably.

**Constraints**

- `logits` has shape `(T, A)`, with `1 <= T <= 1000` and `2 <= A <= 10`
- `actions` is an integer array of shape `(T,)` with values in `[0, A)`
- `rewards` is a float array of shape `(T,)`
- `0 <= gamma <= 1`, `eps > 0`
