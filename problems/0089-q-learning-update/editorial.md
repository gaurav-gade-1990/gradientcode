## Approach

Q-learning is **off-policy TD control**. Whatever action the agent actually takes next, the target bootstraps from the best action in the next state. That's why it learns $Q^*$ even while the agent explores.

$$
Q(s, a) \leftarrow Q(s, a) + \alpha\bigl(\underbrace{r + \gamma \max_{a'} Q(s', a')}_{\text{TD target}} - Q(s, a)\bigr)
$$

At a terminal transition there is no future, so the target is just $r$.

```python
Q = np.array(Q, dtype=float)
for s, a, r, s_next, done in transitions:
    target = r if done else r + gamma * np.max(Q[s_next])
    Q[s, a] += alpha * (target - Q[s, a])
```

The loop has to be sequential. When the same state shows up again later in the stream, its updated value is what the next target sees. That's how reward propagates backward along a trajectory.

## Common mistakes

- **Ignoring `done`.** Bootstrapping past a terminal state adds value that doesn't exist. This is a classic bug in DQN code.
- **Batching the targets.** Computing every target from the original table loses the dependency between consecutive updates.
- **Averaging instead of maxing.** `mean(Q[s'])` is the expected-SARSA target under a uniform policy, not Q-learning.
- **Modifying the input.** `Q[s, a] += ...` on the argument changes the caller's array.

## Complexity

- **Time:** $O(nA)$ for $n$ transitions, from the max over actions.
- **Space:** $O(SA)$ for the copy of the table.
