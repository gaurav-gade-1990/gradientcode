## 1. What the problem is really asking

A multi-armed bandit is the smallest reinforcement-learning problem: no states, just a set of actions with unknown average rewards. You have to keep choosing, and every pull of an arm you're unsure about costs you a pull of the arm you think is best. This is the explore-exploit trade-off behind A/B tests that adapt, prompt-variant selection (problem 152, thompson-prompt-variants) and ad ranking.

Epsilon-greedy is the simplest policy: usually pick the arm with the highest estimated mean, but with probability ε pick a random one. Under the story this is **a sequential loop with two running arrays**, `Q` (estimated means) and `N` (pull counts). All randomness is handed to you as `u` and `explore_arms`, so the run is deterministic.

The judge compares the full sequence of pulled arms exactly and the final `Q` with `rtol=1e-9`. Since each step depends on the last, one wrong pick early on changes everything after it.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `rewards` | `(T, n_arms)` | the reward each arm **would** give at step `t` | read only `rewards[t, a]` for the arm you pull |
| `epsilon` | float in `[0, 1]` | exploration probability | explore when `u[t] < epsilon` |
| `u` | `(T,)` | one uniform per step | the explore coin flip |
| `explore_arms` | `(T,)` int | the random arm to use if exploring | ignored on exploit steps |
| return | `(T,)` int, `(n_arms,)` float | `arms, Q` | the pulls and the final estimates |

The details that are easy to miss:

- **The comparison is strict.** `u[t] == epsilon` means exploit. With `epsilon = 0` you never explore, even when `u[t] = 0`.
- **Ties go to the lowest index.** At step 0 every `Q` is 0, so an exploit step pulls arm 0. `np.argmax` returns the first maximum.
- **`rewards` is a full table, but you only see one entry per step.** That's what makes it a bandit: the rewards of arms you didn't pull are never observed.
- **`Q` starts at 0, not at the first reward.** The incremental update handles the first pull correctly anyway (see section 3).

## 3. The math

**The sample mean, incrementally.** Let $r_1, \dots, r_n$ be the rewards seen from one arm, and $Q_n = \frac1n \sum_{i=1}^n r_i$. Then

$$Q_n = \frac{1}{n}\Big(\sum_{i=1}^{n-1} r_i + r_n\Big) = \frac{1}{n}\big((n-1)\,Q_{n-1} + r_n\big) = Q_{n-1} + \frac{1}{n}\big(r_n - Q_{n-1}\big).$$

So you never store past rewards: one count and one estimate per arm suffice. On the first pull, $n = 1$ and $Q_1 = Q_0 + (r_1 - Q_0) = r_1$, whatever $Q_0$ was. That's why starting at 0 is harmless for the arms you pull, though it matters for arms you **haven't** pulled: they keep $Q = 0$, which the greedy choice compares against.

**Order matters.** The step size is $1/n$ with $n$ the **new** count. Increment $N[a]$ first, then update. Using the old count, or any other denominator, gives a different number.

**Constant step size for comparison.** With $Q \leftarrow Q + \alpha (r - Q)$ and fixed $\alpha$, unrolling gives

$$Q_n = (1 - \alpha)^n Q_0 + \sum_{i=1}^{n} \alpha (1 - \alpha)^{n-i}\, r_i,$$

an exponentially weighted average that favours recent rewards. That's the right choice when arm means drift over time, but it isn't what this problem asks for. With $Q_0 = 0$ and $\alpha = 0.1$, one pull of reward 1 gives $Q = 0.1$, not 1.

**The policy.** At step $t$,

$$a_t = \begin{cases} \texttt{explore\_arms}[t] & u_t < \varepsilon \\ \min \arg\max_a Q[a] & \text{otherwise.} \end{cases}$$

Since $u_t$ is uniform on $[0, 1)$, $\Pr[u_t < \varepsilon] = \varepsilon$ exactly. With the strict inequality, $\varepsilon = 0$ never explores and $\varepsilon = 1$ always does.

**Why explore at all.** Greedy with $\varepsilon = 0$ can lock onto a bad arm forever: once an arm's estimate is the highest, nothing ever tests the others. With $\varepsilon > 0$, every arm is pulled about $\varepsilon T / n_{\text{arms}}$ times, so every estimate converges. The price is that a fraction $\varepsilon$ of pulls stays random forever, so expected regret grows linearly in $T$. Decaying $\varepsilon$ over time, or UCB and Thompson sampling, fix that.

## 4. Trace an example by hand

**Example 1:** `n_arms = 3`, `epsilon = 0.2`.

| t | `u[t]` | mode | arm | reward | `N` after | `Q` after |
|---|---|---|---|---|---|---|
| 0 | `0.9` | exploit, all `Q = 0`, lowest index | 0 | `1` | `[1, 0, 0]` | `[1, 0, 0]` |
| 1 | `0.1` | explore | 1 | `2` | `[1, 1, 0]` | `[1, 2, 0]` |
| 2 | `0.05` | explore | 2 | `5` | `[1, 1, 1]` | `[1, 2, 5]` |
| 3 | `0.5` | exploit | 2 | `4` | `[1, 1, 2]` | `[1, 2, 4.5]` |
| 4 | `0.7` | exploit | 2 | `0` | `[1, 1, 3]` | `[1, 2, 3]` |

Output `([0, 1, 2, 2, 2], [1, 2, 3])`. At step 3 the update is `5 + (4 - 5) / 2 = 4.5`, and at step 4 it's `4.5 + (0 - 4.5) / 3 = 3`, the mean of `5, 4, 0`.

**Example 2** has `epsilon = 0`, so it is pure greedy:

| t | arm | reward | `Q` after |
|---|---|---|---|
| 0 | 0 (tie at 0) | `-1` | `[-1, 0]` |
| 1 | 1 | `0.5` | `[-1, 0.5]` |
| 2 | 1 | `0` | `[-1, 0.25]` |
| 3 | 1 | `1` | `[-1, 0.5]` |

At step 3 arm 0 would have paid `4`, but the agent never tries it again. That's the failure mode exploration exists to prevent.

**The hidden case "u equals epsilon"** has `epsilon = 0.5` and `u = [0.5, 0.5, 0.25]`. Steps 0 and 1 exploit (because `0.5 < 0.5` is false) and pull arm 0; only step 2 explores. Expected arms `[0, 0, 1]`. With `<=`, step 0 explores and pulls arm 1.

## 5. Plan before you code

```
Q = zeros(n_arms);  N = zeros(n_arms);  arms = zeros(T, int)
for t in 0 .. T-1:
    a = explore_arms[t] if u[t] < epsilon else argmax(Q)
    N[a] += 1
    Q[a] += (rewards[t, a] - Q[a]) / N[a]
    arms[t] = a
return arms, Q
```

| situation | rule | wrong versions |
|---|---|---|
| explore test | `u[t] < epsilon` | `<=` explores when `epsilon = 0` |
| exploit tie | `np.argmax(Q)`, first max | reversing `Q` picks the last max |
| update | count first, then `/ N[a]` | constant `0.1`, or the old count |

## 6. Build it one piece at a time

**Step 1: state.**

```python
T, n_arms = rewards.shape
Q = np.zeros(n_arms)            # (n_arms,) estimated mean reward
N = np.zeros(n_arms)            # (n_arms,) pull counts
arms = np.zeros(T, dtype=int)   # (T,) the trajectory, integer dtype
```

**Step 2: choose an arm.**

```python
a = int(explore_arms[t]) if u[t] < epsilon else int(np.argmax(Q))
```

`int(...)` turns a NumPy integer into a plain Python index; either works for indexing, but it keeps `a` simple.

**Step 3: update the chosen arm only.**

```python
N[a] += 1
Q[a] += (rewards[t, a] - Q[a]) / N[a]
arms[t] = a
```

There's no vectorisation across `t`: step `t + 1`'s choice depends on `Q` after step `t`. The only array operation per step is the `argmax` over `n_arms` values.

## 7. Full solution

```python
# NumPy for the arrays and argmax
import numpy as np


# rewards: (T, n_arms); u, explore_arms: (T,); returns (arms (T,), Q (n_arms,))
def epsilon_greedy(rewards: np.ndarray, epsilon: float, u: np.ndarray, explore_arms: np.ndarray) -> tuple:
    T, n_arms = rewards.shape  # number of steps and number of arms
    Q = np.zeros(n_arms)  # (n_arms,) running mean reward per arm; untried arms stay at 0
    N = np.zeros(n_arms)  # (n_arms,) how many times each arm has been pulled
    arms = np.zeros(T, dtype=int)  # (T,) the arm pulled at each step
    # sequential by nature: each choice depends on the estimates so far
    for t in range(T):
        # strict < so epsilon = 0 never explores; argmax returns the lowest index on ties
        a = int(explore_arms[t]) if u[t] < epsilon else int(np.argmax(Q))
        N[a] += 1  # count this pull first, so the step size is 1 / (new count)
        Q[a] += (rewards[t, a] - Q[a]) / N[a]  # incremental sample mean; first pull sets Q to the reward
        arms[t] = a  # record the trajectory for the judge
    # the pulls and the final estimates
    return arms, Q
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `([0, 1, 2, 2, 2], [1, 2, 3])` | explore and exploit steps, the incremental mean |
| Example 2 | `([0, 1, 1, 1], [-1, 0.5])` | `epsilon = 0` never explores, even with `u = 0` |
| u equals epsilon | `([0, 0, 1], [0, 1])` | the strict `<` |
| epsilon = 1 | every arm comes from `explore_arms` | always exploring; the tie rule never runs |
| single arm | `Q = [1.0435]`, all pulls arm 0 | `n_arms = 1`; `Q` is the plain mean of 12 rewards |
| all-zero rewards ties | `([0, 0, 0, 0, 0, 2, 0, 0], [0, 0, 0])` | every exploit is a three-way tie, so it pulls arm 0 |
| long run | 405 of 500 pulls go to arm 2 (true mean 0.9) | the agent finds the best arm |
| many arms | 504 of 800 pulls go to arm 3 | 8 arms, `epsilon = 0.05` |

## 9. Complexity

Each step costs $O(n_{\text{arms}})$ for the `argmax` and $O(1)$ for the update, so the run is $O(T \cdot n_{\text{arms}})$ time and $O(n_{\text{arms}} + T)$ memory, including the output.

In production the loop is an online service: each request picks an arm, the reward (a click, a thumbs-up, a conversion) arrives later, and the update is applied when it does. Delayed and batched feedback, plus rewards that drift over time, are why real systems often use a constant step size or a sliding window instead of the exact mean, and why they log the propensity (the probability the chosen arm had) for unbiased offline evaluation.

## 10. If you got Wrong Answer

- **`Q` is ten times too small after one pull (Example 1 gives `Q[0] = 0.1`, expected `1`).** You used a constant step size `0.1` (`wrong_constant_step.py`). It passes only "all-zero rewards ties", where every reward is 0.
- **`Q` is half what it should be after one pull (`0.5` instead of `1`).** Your denominator isn't the new count. `wrong_update_before_count.py` updates first and divides by `N[a] + 2`; updating first with `/ N[a]` would divide by zero on the first pull.
- **Example 2 or "u equals epsilon" starts with arm 1 instead of 0.** You explored on `u[t] <= epsilon` (`wrong_explore_le.py`).
- **Exploit steps pick the highest index on ties (Example 1 starts with arm 2).** You broke ties toward the last arm (`wrong_ties_last_arm.py`). It passes only "epsilon = 1" and "single arm", where no tie is ever broken.
- **`arms` has a float dtype.** Create it with `dtype=int`.

## 11. Follow-ups an interviewer might ask

- *How would you make exploration smarter?* UCB picks $\arg\max_a Q[a] + c\sqrt{\ln t / N[a]}$, a bonus that shrinks as an arm is tried. Thompson sampling draws a plausible mean per arm from its posterior and picks the best draw (problem 152, thompson-prompt-variants).
- *How does this relate to full RL?* Q-learning keeps the same "estimate plus step size times error" update, but per state and with a bootstrapped target (problem 89, q-learning-update).
- *What if the best arm changes over time?* Use a constant step size or a sliding window so old rewards fade, and keep `epsilon` above zero.
- *What if rewards depend on the user?* That's a contextual bandit: replace the per-arm mean with a model of reward given features, e.g. LinUCB.
- *How do you know whether the winner is really better?* Compare the arms' outcomes with a significance test (problem 146, ab-test-significance), keeping in mind that adaptive allocation biases naive estimates.
