Simulate an **epsilon-greedy** agent on a multi-armed bandit. All randomness is given to you, so the run is deterministic.

The bandit has `n_arms` arms and runs for `T` steps. `rewards[t, a]` is the reward you get if you pull arm `a` at step `t`. Keep a value estimate `Q[a]` and a pull count `N[a]` for every arm, all starting at `0`.

At each step `t = 0, 1, ..., T - 1`:

1. If `u[t] < epsilon` (strictly), **explore**: pull arm `explore_arms[t]`.
2. Otherwise, **exploit**: pull the arm with the largest `Q`. If several arms tie, pull the one with the lowest index.
3. With `a` the arm you pulled and `r = rewards[t, a]`, update the sample mean incrementally:

$$
N[a] \leftarrow N[a] + 1, \qquad Q[a] \leftarrow Q[a] + \frac{r - Q[a]}{N[a]}
$$

Return a tuple `(arms, Q)`: `arms` is an integer array of shape `(T,)` holding the arm pulled at each step, and `Q` is the final float array of shape `(n_arms,)`.

**Constraints**

- `rewards` is a float array of shape `(T, n_arms)`, with `1 <= T <= 2000` and `1 <= n_arms <= 20`
- `0 <= epsilon <= 1`
- `u` is a float array of shape `(T,)` with values in `[0, 1)`
- `explore_arms` is an integer array of shape `(T,)` with values in `[0, n_arms)`
