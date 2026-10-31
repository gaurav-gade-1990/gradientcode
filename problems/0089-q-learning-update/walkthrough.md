## 1. What the problem is really asking

Value iteration (problem 88) needs the full transition model `P` and reward table `R`. Real agents don't have them. They only see what happened: "in state `s` I took action `a`, got reward `r`, and landed in `s_next`". Q-learning learns the optimal action values from a stream of those transitions alone, one small correction at a time. It's the algorithm under DQN and much of modern value-based RL.

Under the story this is **a sequential loop of in-place scalar updates on a table**: for each transition, compute a target, then move one cell a fraction `alpha` of the way toward it. The only subtleties are when to bootstrap (not on terminal transitions) and that each update must see every earlier one.

The judge compares your returned `(S, A)` table with `rtol=1e-9`, so the exact order of updates matters.

## 2. Understand the inputs

| name | type / shape | what it is | how you use it |
|---|---|---|---|
| `Q` | `(S, A)` float | the current action-value table | copied, then updated cell by cell |
| `transitions` | list of `(s, a, r, s_next, done)` | observed experience, in order | one update each |
| `alpha` | float in `(0, 1]` | learning rate | fraction of the error to correct |
| `gamma` | float in `[0, 1]` | discount factor | weight of the bootstrapped future |
| return | `(S, A)` float | the updated table | a new array |

The details that are easy to miss:

- **`done` means there is no future.** The target is just `r`. `Q[s_next]` may hold any value, and it must be ignored.
- **Order matters.** A later transition must see values written by earlier ones. Computing all targets from the original table gives a different answer.
- **The target uses the max over next actions**, not the mean and not the action actually taken next. That's what makes it Q-learning rather than SARSA.
- **Don't modify `Q` in place.** Copy it with a float dtype first, so an integer table can't truncate updates either.

## 3. The math

**The Bellman equation for $Q^*$.** The optimal action value satisfies

$$Q^*(s, a) = \mathbb{E}\Big[r + \gamma \max_{a'} Q^*(s', a') \,\Big|\, s, a\Big],$$

with the expectation over the reward and next state. On a terminal transition there's no $s'$ to continue from, so the bracket is just $r$.

**From an expectation to a sample.** You can't compute the expectation without the model, but each observed transition gives one sample of the quantity inside it, the **TD target**:

$$y = \begin{cases} r & \text{done} \\ r + \gamma \max_{a'} Q(s', a') & \text{otherwise.} \end{cases}$$

**The update as a running average.** Moving toward the target by a fraction $\alpha$,

$$Q(s, a) \leftarrow Q(s, a) + \alpha\big(y - Q(s, a)\big) = (1 - \alpha)\, Q(s, a) + \alpha\, y,$$

is the same "old estimate plus step size times error" rule as the bandit mean (problem 87, epsilon-greedy-bandit). The difference $\delta = y - Q(s, a)$ is the **TD error**.

**As gradient descent.** Treat $y$ as a fixed label and minimise the squared error $\tfrac12 (y - Q(s, a))^2$ with respect to the table entry $Q(s, a)$:

$$\frac{\partial}{\partial Q(s, a)}\, \tfrac12\big(y - Q(s, a)\big)^2 = -\big(y - Q(s, a)\big).$$

One gradient step of size $\alpha$ is exactly the update above. "Treat $y$ as fixed" is a real choice: $y$ depends on $Q$ too, but you don't differentiate through it. That's why it's called a **semi-gradient** method, and why DQN uses a frozen target network for $y$.

**Why the max.** The max makes the target the value of acting **greedily** from $s'$, whatever the agent actually does next. So Q-learning is **off-policy**: it learns $Q^*$ while the data comes from an exploring policy. With enough visits to every pair and suitably decaying $\alpha$, it converges to $Q^*$.

**Self-loop fixed point.** In the hidden case "self loop", one state with reward 1 loops to itself, $\gamma = 0.8$. The fixed point solves $Q = 1 + 0.8\,Q$, so $Q = 5$. Six updates at $\alpha = 0.5$ get only part of the way, which is why the expected value is `2.3428`, not 5.

## 4. Trace an example by hand

**Example 1:** `Q = zeros((3, 2))`, `alpha = 0.5`, `gamma = 0.9`.

| step | transition `(s, a, r, s_next, done)` | target `y` | `Q[s, a]` before | `Q[s, a]` after |
|---|---|---|---|---|
| 1 | `(0, 1, 1.0, 1, False)` | `1 + 0.9 · max(Q[1]) = 1 + 0 = 1` | `0` | `0 + 0.5 · (1 − 0) = 0.5` |
| 2 | `(1, 0, 2.0, 2, True)` | `2` (done, no bootstrap) | `0` | `0.5 · 2 = 1` |
| 3 | `(0, 1, 0.0, 1, False)` | `0 + 0.9 · max(Q[1]) = 0.9 · 1 = 0.9` | `0.5` | `0.5 + 0.5 · (0.9 − 0.5) = 0.7` |

Step 3 reads `Q[1, 0] = 1`, the value step 2 just wrote. Computing every target from the original zeros gives `0.5` instead of `0.7`.

**Example 2** uses `alpha = 1`, so each cell is replaced by its target: `Q[0, 0] = -1 + 0.5 · max(3, -1) = 0.5`, then `Q[1, 1] = 5` (done). If you bootstrap on the terminal transition, `Q[1, 1]` becomes `5 + 0.5 · max(Q[0]) = 5 + 0.5 · 2 = 6`.

**The hidden case "self loop"** applies `(0, 0, 1.0, 0, False)` six times:

| update | target `1 + 0.8 · max(Q[0])` | `Q[0, 0]` after |
|---|---|---|
| 1 | `1` | `0.5` |
| 2 | `1.4` | `0.95` |
| 3 | `1.76` | `1.355` |
| 4 | `2.084` | `1.7195` |
| 5 | `2.3756` | `2.0476` |
| 6 | `2.638` | `2.3428` |

Each target is computed from the value written one step earlier. With batched targets every update sees `Q = 0`, so all six targets are 1 and the result is `3`.

**The hidden case "chain dependency"** shows why order matters. The three transitions run backward along a chain, `2 → 3` (reward 1, done), then `1 → 2`, then `0 → 1`, with `alpha = 1`, `gamma = 0.9`. The reward flows back in one pass: `Q = [0.81, 0.9, 1, 0]`. In forward order the same transitions would give `[0, 0, 1, 0]`, because states 0 and 1 would read their successors before those were updated.

## 5. Plan before you code

```
Q = float copy of the input
for (s, a, r, s_next, done) in transitions, in order:
    y = r if done else r + gamma * max(Q[s_next])
    Q[s, a] += alpha * (y - Q[s, a])
return Q
```

| part | correct | common wrong version |
|---|---|---|
| terminal | `y = r` | `r + gamma * max(Q[s_next])` always |
| bootstrap | `max(Q[s_next])` | `mean(Q[s_next])` |
| table read | the live, updated `Q` | the original `Q0` |

## 6. Build it one piece at a time

**Step 1: copy.**

```python
Q = np.array(Q, dtype=float)    # (S, A), a new float array
```

`np.array` copies by default. `dtype=float` also protects against an integer input table, where `+=` with a fraction would truncate.

**Step 2: the target.**

```python
target = r if done else r + gamma * np.max(Q[s_next])
```

`Q[s_next]` is row `s_next`, shape `(A,)`, and `np.max` reduces it to one number: the value of the best next action.

**Step 3: the update.**

```python
Q[s, a] += alpha * (target - Q[s, a])
```

Only one cell changes. Because the loop writes into the same `Q` it reads from, the next transition automatically sees this value.

## 7. Full solution

```python
# NumPy for the table copy and the max over next actions
import numpy as np


# Q: (S, A) table; transitions: list of (s, a, r, s_next, done); returns a new (S, A) table
def q_learning(Q: np.ndarray, transitions: list, alpha: float, gamma: float) -> np.ndarray:
    # copy as float, so the caller's table is untouched and fractional updates aren't truncated
    Q = np.array(Q, dtype=float)
    # strictly in order: each update must see every earlier one
    for s, a, r, s_next, done in transitions:
        # terminal: no future to bootstrap; otherwise reward plus discounted best next action
        target = r if done else r + gamma * np.max(Q[s_next])
        # move this one cell a fraction alpha of the way toward the target (the TD error)
        Q[s, a] += alpha * (target - Q[s, a])
    # the updated table
    return Q
```

## 8. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `Q[0, 1] = 0.7`, `Q[1, 0] = 1` | sequential updates; a done transition |
| Example 2 | `Q = [[0.5, 2], [3, 5]]` | `alpha = 1` replaces the cell; done skips the bootstrap |
| no transitions | the input table unchanged | an empty stream returns a copy |
| terminal bootstrap ignored | `Q[0, 0] = 7.3` | a table full of `10`s must not leak into done targets |
| self loop | `Q[0, 0] = 2.3428` | six updates, each reading the last write |
| chain dependency | `Q = [0.81, 0.9, 1, 0]` | reward propagates backward through the live table |
| negative values max | `Q[0] = [-1.1578, -1.0151, -1.1787, -1.3436]` | the max of all-negative rows; nothing is clipped at 0 |
| gamma = 1 | `Q[0, 0] = 0.357306` | no discounting, random transitions with some done |
| long stream | 2000 transitions, `Q[0, 0] = 0.0226981` | many interleaved updates |

## 9. Complexity

Each transition costs $O(A)$ for the max over the next row and $O(1)$ for the update, so $n$ transitions take $O(nA)$ time. Memory is $O(SA)$ for the copy.

The tabular version stops scaling when the state space does: a table needs one cell per state-action pair, and an agent playing from pixels never visits the same state twice. DQN replaces the table with a neural network $Q_\theta(s, \cdot)$, minimises the same squared TD error by gradient descent, samples transitions from a replay buffer to break their correlation, and computes targets with a slowly updated copy of the network so they don't chase themselves.

## 10. If you got Wrong Answer

- **Example 1 gives `Q[0, 1] = 0.5` instead of `0.7`.** You computed every target from the original table (`wrong_batched_targets.py`). "self loop" gives `3` and "chain dependency" gives `0` at `Q[0, 0]`.
- **Example 2 gives `Q[1, 1] = 6` instead of `5`, and "terminal bootstrap ignored" gives `10` instead of `7.3`.** You bootstrapped on done transitions (`wrong_ignore_done.py`). Example 1 still passes, because the terminal transition there lands in a row of zeros.
- **Example 2 gives `Q[0, 0] = -0.5` instead of `0.5`.** You used `np.mean(Q[s_next])` (`wrong_sarsa_mean.py`). That's expected SARSA under a uniform policy, not Q-learning.
- **The caller's table changed after your call.** You updated the argument in place. Copy it first.

## 11. Follow-ups an interviewer might ask

- *What's the difference between Q-learning and SARSA?* SARSA bootstraps from the action the agent actually takes next, $Q(s', a')$, so it learns the value of its own exploring policy (on-policy). Q-learning uses the max, so it learns the greedy policy's value (off-policy).
- *Why does Q-learning overestimate?* The max of noisy estimates is biased upward. Double Q-learning picks the argmax with one table and evaluates it with another.
- *Where does the data come from?* Usually an epsilon-greedy policy over the current Q (problem 87, epsilon-greedy-bandit), with epsilon decayed over time.
- *How does this relate to value iteration?* Value iteration applies the full expected Bellman backup to every state each sweep (problem 88, value-iteration). Q-learning applies a one-sample version to one state-action pair per transition.
- *How do you handle episodes cut off by a time limit?* A time-limit truncation is not a true terminal state, so you should still bootstrap there. Treating it as `done` biases the values down.
