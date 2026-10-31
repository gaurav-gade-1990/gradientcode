## 1. What the problem is really asking

Policy-gradient methods like PPO and A2C push up the probability of actions that turned out **better than expected** and push down the rest. "Better than expected" is the advantage, $A_t = Q(s_t, a_t) - V(s_t)$, and it has to be estimated from a rollout. Generalized Advantage Estimation is the standard estimator. Nearly every PPO implementation, including the ones used for RLHF on language models, computes exactly this function.

Under the story this is **a vectorised one-step error, followed by a backward scan with a reset mask**. The scan is a discounted cumulative sum that restarts wherever an episode ended. The work is getting the mask in the right two places and bootstrapping from `last_value` at the end of the rollout.

The judge compares both returned arrays, `advantages` and `returns`, with `rtol=1e-9`, for 1-D rollouts and for `(T, N)` batches of parallel environments.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `rewards` | `(T,)` or `(T, N)` | $r_t$, reward after the action at step `t` | in every $\delta_t$ |
| `values` | same | critic estimates $V(s_t)$ | subtracted in $\delta_t$, shifted for $V(s_{t+1})$ |
| `dones` | same, bool or 0/1 | episode ended after step `t` | mask $m_t = 1 - \text{done}_t$ |
| `last_value` | float or `(N,)` | $V(s_T)$, the state after the last step | the final $V(s_{t+1})$ |
| `gamma`, `lam` | floats in `[0, 1]` | discount and GAE weight | $\gamma$ and $\gamma\lambda$ |
| return | same as `rewards`, twice | `advantages, returns` | `returns = advantages + values` |

The details that are easy to miss:

- **`dones[t]` describes the transition out of step `t`.** If it's 1, $s_{t+1}$ is the first state of a **new** episode, so step `t` must not look at it. Use `dones[t]`, not `dones[t + 1]`.
- **The mask appears twice**: in $\delta_t$ (no bootstrap across the boundary) and in the recursion (no advantage leaks backward across it).
- **`last_value` is real information.** A rollout usually stops mid-episode, and the steps near the end still have a future. Only a done flag on the last step makes it irrelevant.
- **Time is axis 0.** Index `[t]` gives a scalar for `(T,)` inputs and an `(N,)` row for `(T, N)` inputs, so one loop handles both.

## 3. The math

**The one-step TD error.** With $V(s_T) = \texttt{last\_value}$ and $m_t = 1 - \text{done}_t$,

$$\delta_t = r_t + \gamma\, m_t\, V(s_{t+1}) - V(s_t).$$

If $V$ were the true value function of the policy, $\mathbb{E}[\delta_t \mid s_t, a_t] = Q(s_t, a_t) - V(s_t)$: the TD error is an unbiased advantage estimate. With a learned critic it's biased, but it has low variance because it involves only one reward.

**$n$-step estimates.** Within one episode (all $m = 1$), look $n$ steps ahead before bootstrapping:

$$\hat A_t^{(n)} = \sum_{l=0}^{n-1} \gamma^l r_{t+l} + \gamma^n V(s_{t+n}) - V(s_t).$$

Each $V(s_{t+l})$ for $0 < l < n$ cancels when you add consecutive TD errors, so

$$\hat A_t^{(n)} = \sum_{l=0}^{n-1} \gamma^l \delta_{t+l}.$$

Check $n = 2$: $\delta_t + \gamma\delta_{t+1} = r_t + \gamma V(s_{t+1}) - V(s_t) + \gamma r_{t+1} + \gamma^2 V(s_{t+2}) - \gamma V(s_{t+1})$, and the $\gamma V(s_{t+1})$ terms cancel.

Small $n$ trusts the critic (low variance, more bias). Large $n$ trusts the sampled rewards (less bias, more variance).

**GAE averages all of them.** Weight $\hat A^{(n)}_t$ by $(1 - \lambda)\lambda^{n-1}$, which sums to 1 over $n \ge 1$:

$$A_t = (1 - \lambda)\sum_{n \ge 1} \lambda^{n-1} \sum_{l=0}^{n-1} \gamma^l \delta_{t+l}.$$

Swap the sums: $\delta_{t+l}$ appears in every $\hat A^{(n)}$ with $n > l$, with total weight $(1 - \lambda)\sum_{n > l} \lambda^{n-1} = \lambda^l$. So

$$A_t = \sum_{l \ge 0} (\gamma\lambda)^l\, \delta_{t+l}.$$

$\lambda = 0$ gives $A_t = \delta_t$ (one-step TD). $\lambda = 1$ gives $\sum_l \gamma^l \delta_{t+l}$, which telescopes to the Monte Carlo return minus $V(s_t)$.

**The backward recursion.** Split off the first term:

$$A_t = \delta_t + \gamma\lambda \sum_{l \ge 0} (\gamma\lambda)^l \delta_{t+1+l} = \delta_t + \gamma\lambda\, A_{t+1}.$$

At an episode boundary the sum must stop, so multiply by the mask: $A_t = \delta_t + \gamma\lambda\, m_t\, A_{t+1}$, with $A_T = 0$. This turns an $O(T^2)$ sum into one $O(T)$ pass from the end.

**Value targets.** $\text{returns}_t = A_t + V(s_t)$ is the $\lambda$-return, the target the critic is regressed onto in PPO.

## 4. Trace an example by hand

**Example 2:** `rewards = [0, 1, 0, 2]`, `values = [1, 2, 1, 0]`, `dones = [F, T, F, F]`, `last_value = 3`, `gamma = lam = 1`.

The shifted values are `next_values = [2, 1, 0, 3]` (the last one is `last_value`), and the mask is `[1, 0, 1, 1]`.

| t | `r_t` | `m_t` | `V(s_{t+1})` | `δ_t = r + m·V' − V` |
|---|---|---|---|---|
| 0 | 0 | 1 | 2 | `0 + 2 − 1 = 1` |
| 1 | 1 | 0 | (ignored) | `1 + 0 − 2 = −1` |
| 2 | 0 | 1 | 0 | `0 + 0 − 1 = −1` |
| 3 | 2 | 1 | 3 | `2 + 3 − 0 = 5` |

Now scan backward with `A_t = δ_t + m_t · A_{t+1}`:

| t | computation | `A_t` | `returns_t = A_t + V_t` |
|---|---|---|---|
| 3 | `5 + 1 · 0` | `5` | `5` |
| 2 | `−1 + 1 · 5` | `4` | `5` |
| 1 | `−1 + 0 · 4` | `−1` | `1` |
| 0 | `1 + 1 · (−1)` | `0` | `1` |

Output `([0, -1, 4, 5], [1, 1, 5, 5])`. Step 1 ended the episode, so the `4` from the next episode doesn't flow into it. Without the mask in the recursion, `A_1 = −1 + 4 = 3` and `A_0 = 4`.

**Example 1** has no dones and constant values: every `δ = 1 + 0.9 · 0.5 − 0.5 = 0.95`, and with `γλ = 0.72` the scan gives `A = [2.12648, 1.634, 0.95]`.

**The hidden case "done on last step"** sets `last_value = 100` and `dones[2] = 1`. The mask zeroes it out, so `A_2 = 3 − 0.3 = 2.7`. Bootstrapping from `100` would give a huge advantage for a state that had no future.

## 5. Plan before you code

```
mask = 1 - dones                                  # same shape as rewards
next_values = values[1:] followed by last_value   # V(s_{t+1})
deltas = rewards + gamma * mask * next_values - values
running = 0 (shape of one time step)
for t from T-1 down to 0:
    running = deltas[t] + gamma * lam * mask[t] * running
    adv[t] = running
returns = adv + values
```

| line | `(T,)` inputs | `(T, N)` inputs |
|---|---|---|
| `np.asarray(last_value)[None]` | `()` → `(1,)` | `(N,)` → `(1, N)` |
| `concatenate([values[1:], ...], axis=0)` | `(T,)` | `(T, N)` |
| `deltas[t]`, `running` | scalars | `(N,)` rows |

## 6. Build it one piece at a time

**Step 1: float arrays and the mask.**

```python
rewards = np.asarray(rewards, dtype=float)
values = np.asarray(values, dtype=float)
mask = 1.0 - np.asarray(dones, dtype=float)       # bools become 0.0 / 1.0
```

Converting first makes the mask a float array whatever dtype `dones` arrives in, and `dones - something_bool` (bool minus bool) would raise a `TypeError`.

**Step 2: shift the values by one step.**

```python
next_values = np.concatenate([values[1:], np.asarray(last_value, dtype=float)[None]], axis=0)
```

`[None]` adds a leading axis of length 1, so `last_value` becomes one more "time step" whether it's a scalar or an `(N,)` vector.

**Step 3: all TD errors at once.**

```python
deltas = rewards + gamma * mask * next_values - values     # same shape as rewards
```

Everything is element-wise between arrays of the same shape; there's no broadcasting across axes.

**Step 4: the backward scan.**

```python
adv = np.zeros_like(rewards)
running = np.zeros_like(rewards[0])               # scalar or (N,)
for t in range(len(rewards) - 1, -1, -1):
    running = deltas[t] + gamma * lam * mask[t] * running
    adv[t] = running
```

The scan can't be vectorised directly because each step needs the next one, but each step is a single vector operation over the `N` environments.

## 7. Full solution

```python
# NumPy for the vectorised TD errors and the per-step scan
import numpy as np


# Inputs (T,) or (T, N) with time on axis 0; returns (advantages, returns) of the same shape
def gae(rewards: np.ndarray, values: np.ndarray, dones: np.ndarray, last_value, gamma: float = 0.99, lam: float = 0.95) -> tuple:
    rewards = np.asarray(rewards, dtype=float)  # float copy so arithmetic is exact and bools can't sneak in
    values = np.asarray(values, dtype=float)  # V(s_t) for every step
    mask = 1.0 - np.asarray(dones, dtype=float)  # 0 where the episode ended after step t, else 1
    # V(s_{t+1}): values shifted by one, with last_value as the state after the final step
    next_values = np.concatenate([values[1:], np.asarray(last_value, dtype=float)[None]], axis=0)
    # one-step TD errors; the mask stops step t from bootstrapping into the next episode
    deltas = rewards + gamma * mask * next_values - values

    adv = np.zeros_like(rewards)  # output, same shape as rewards
    running = np.zeros_like(rewards[0])  # A_{t+1}, starts at A_T = 0; scalar or (N,)
    # walk backward so each A_t can reuse A_{t+1}
    for t in range(len(rewards) - 1, -1, -1):
        # A_t = delta_t + gamma*lam*m_t*A_{t+1}; the mask cuts the sum at episode boundaries
        running = deltas[t] + gamma * lam * mask[t] * running
        adv[t] = running  # store this step's advantage
    # the lambda-return A_t + V(s_t) is the critic's regression target
    return adv, adv + values
```

## 8. How the test cases map to the code

| test case | expected (advantages) | what it checks |
|---|---|---|
| Example 1 | `[2.12648, 1.634, 0.95]` | the backward recursion with no boundaries |
| Example 2 | `[0, -1, 4, 5]` | a done in the middle resets the scan |
| lam = 0 is one-step TD | advantages equal the deltas | `λ = 0`: no recursion at all |
| done on last step | `[4.8464, 4.3935, 2.7]` | `last_value = 100` must be masked out |
| done on first step | `[3, -0.8434, -0.8695, -0.9]` | `A_0 = δ_0 = 5 − 2`, isolated from later steps |
| single step | `[1.29]` | `T = 1` with default `γ, λ`: `0.5 + 0.99 · 1 − 0.2` |
| consecutive dones | `[1, -1.3, 2.6753, 0.1, 0.482]` | one-step episodes in a row |
| parallel envs | shape `(64, 4)` | `(T, N)` inputs, `last_value` of shape `(N,)` |
| long rollout | `T = 2048`, `γ = 0.999` | a long scan, rare dones |

## 9. Complexity

The TD errors are one vectorised pass and the scan is $T$ steps of $O(N)$ work, so the total is $O(TN)$ time and $O(TN)$ memory.

In a PPO training loop this is negligible next to the forward and backward passes of the policy and critic networks. What matters at scale is correctness at boundaries: parallel environments reset at different times, rollouts are cut by a fixed horizon (where `last_value` provides the bootstrap), and episodes that end because of a time limit should arguably be bootstrapped rather than masked. In RLHF for language models, each response is usually one episode, the reward arrives on the last token, and per-token KL penalties are added to the intermediate rewards before GAE runs.

## 10. If you got Wrong Answer

- **Advantages leak across episodes (Example 2 gives `A_0 = 4` instead of `0`).** You masked $\delta_t$ but not the recursion (`wrong_mask_delta_only.py`). It passes the cases without a done in the middle.
- **Example 2 gives `A_0 = -1` and "done on last step" is far off.** You used `dones[t + 1]` (`wrong_next_done.py`). The mask for step `t` must come from `dones[t]`.
- **The last steps are too small (Example 1 gives `1.8932` instead of `2.12648`).** You bootstrapped the final step from 0 instead of `last_value` (`wrong_no_bootstrap.py`). It passes "done on last step", where the mask hides the difference anyway.
- **`advantages` are right but `returns` are wrong (Example 1 gives `3.0745` instead of `2.62648`).** You returned discounted Monte Carlo returns (`wrong_returns_monte_carlo.py`). With `γ = λ = 1` they coincide, which is why Example 2 passes.

## 11. Follow-ups an interviewer might ask

- *How do you pick `lam`?* It's the bias-variance knob: `0.95` to `0.97` is standard for PPO. Lower it when the critic is good and rewards are noisy.
- *Why normalise advantages per batch?* Subtracting the mean and dividing by the standard deviation keeps the policy step size stable across tasks with different reward scales.
- *How are the advantages used?* As the weight on $\nabla \log \pi(a_t \mid s_t)$ in the policy gradient (problem 91, reinforce-loss-gradient), clipped by the PPO ratio.
- *What changes for truncated episodes?* Bootstrap from $V(s_{t+1})$ instead of masking, because the true episode would have continued.
- *How does this relate to value iteration?* Both are built on the Bellman equation; GAE estimates from samples what value iteration computes exactly with a model (problem 88, value-iteration).
