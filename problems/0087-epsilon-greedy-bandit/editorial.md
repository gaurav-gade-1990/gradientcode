## Approach

Epsilon-greedy is the simplest answer to the explore-exploit tradeoff. Most of the time, pull the arm that looks best. With probability $\varepsilon$, pull an arm at random to keep learning about the others.

The estimate $Q[a]$ is the sample mean of the rewards from arm $a$. You don't need to store every reward: the mean after $n$ samples updates in place.

$$
Q_n = Q_{n-1} + \frac{1}{n}\bigl(r_n - Q_{n-1}\bigr)
$$

That's the same "old estimate plus step size times error" form used in TD learning, with step size $1/n$.

```python
T, n_arms = rewards.shape
Q, N = np.zeros(n_arms), np.zeros(n_arms)
arms = np.zeros(T, dtype=int)
for t in range(T):
    a = int(explore_arms[t]) if u[t] < epsilon else int(np.argmax(Q))
    N[a] += 1
    Q[a] += (rewards[t, a] - Q[a]) / N[a]
    arms[t] = a
```

Each step depends on the previous one, so the loop over `t` is inherent. `np.argmax` returns the first maximum, which handles the tie-break.

## Common mistakes

- **Constant step size.** `Q += 0.1 * (r - Q)` is an exponential moving average, which suits non-stationary bandits, but it isn't the sample mean.
- **`u <= epsilon`.** The comparison is strict, so `epsilon = 0` never explores.
- **Breaking ties toward the last arm.** Reversing the array or using `>=` in a manual loop picks the highest index.
- **Updating Q before incrementing N.** That gives the wrong denominator.

## Complexity

- **Time:** $O(T \cdot n_{\text{arms}})$, from the argmax at every step.
- **Space:** $O(n_{\text{arms}})$ for $Q$ and $N$, plus $O(T)$ for the output.
