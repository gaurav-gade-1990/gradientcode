Compute **Generalized Advantage Estimation** (Schulman et al., 2016) over a rollout, as used in PPO and A2C.

You get a rollout of `T` steps, possibly from `N` parallel environments:

- `rewards[t]`: the reward received after the action at step `t`.
- `values[t]`: the critic's estimate $V(s_t)$.
- `dones[t]`: `1` (or `True`) if the episode ended after step `t`. Then $s_{t+1}$ is the first state of a new episode and must not be bootstrapped.
- `last_value`: $V(s_T)$, the critic's value for the state after the final step.

Let $V(s_T) = \texttt{last\_value}$ and $m_t = 1 - \text{dones}[t]$. Compute

$$
\delta_t = r_t + \gamma\, m_t\, V(s_{t+1}) - V(s_t)
$$

$$
A_t = \delta_t + \gamma\lambda\, m_t\, A_{t+1}, \qquad A_T = 0
$$

and the value targets $\text{returns}_t = A_t + V(s_t)$.

Return a tuple `(advantages, returns)` of float arrays with the same shape as `rewards`.

**Constraints**

- `rewards`, `values` and `dones` all have shape `(T,)` or all have shape `(T, N)`; time is axis 0
- `last_value` is a float when the inputs are `(T,)`, and an array of shape `(N,)` when they are `(T, N)`
- `dones` is a bool or float array of 0s and 1s
- `1 <= T <= 2048`, `1 <= N <= 16`, `0 <= gamma <= 1`, `0 <= lam <= 1`
