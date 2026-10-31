## Approach

The one-step TD error $\delta_t$ is a low-variance, high-bias advantage estimate. The Monte Carlo return minus $V(s_t)$ is the opposite. GAE takes an exponentially weighted average of all the $n$-step estimates, and that average collapses to a discounted sum of TD errors:

$$
A_t = \sum_{l \ge 0} (\gamma\lambda)^l\,\delta_{t+l}
$$

$\lambda = 0$ gives one-step TD. $\lambda = 1$ gives the Monte Carlo advantage.

Computing the sum backward turns it into a recursion. The done mask has to appear in **two** places: in $\delta_t$, so the value of the next episode's first state isn't bootstrapped, and in the recursion, so advantages don't leak across the boundary.

```python
mask = 1.0 - dones
next_values = np.concatenate([values[1:], np.asarray(last_value)[None]], axis=0)
deltas = rewards + gamma * mask * next_values - values
adv = np.zeros_like(rewards)
running = np.zeros_like(rewards[0])
for t in range(T - 1, -1, -1):
    running = deltas[t] + gamma * lam * mask[t] * running
    adv[t] = running
returns = adv + values
```

The deltas are vectorized. Only the backward scan needs a loop. Because time is axis 0, the same code handles `(T, N)` parallel environments.

`returns = A + V` is the $\lambda$-return, the regression target PPO uses for the critic.

## Common mistakes

- **Masking only $\delta_t$.** The recursion keeps adding the next episode's advantages.
- **Using `dones[t + 1]`.** The flag for step $t$ says whether $s_{t+1}$ belongs to the same episode.
- **Ignoring `last_value`.** A rollout that's cut off mid-episode still has a future. Treating it as $0$ biases the last steps.
- **Monte Carlo returns as targets.** The critic target is $A_t + V(s_t)$, not the discounted reward sum.

## Complexity

- **Time:** $O(TN)$.
- **Space:** $O(TN)$ for the deltas and the output.
