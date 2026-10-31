## 1. What the problem is really asking

A Markov decision process describes a world where, in each state, you choose an action, collect a reward and land in a random next state. Value iteration computes how much long-run discounted reward each state is worth when you act optimally, and from that, the best action in each state. It's the dynamic-programming core that Q-learning (problem 89) and policy-gradient methods (problems 90 and 91) approximate when the model isn't known.

Under the story this is **a fixed-point iteration: one batched matrix-vector product and a max, repeated until the values stop moving**, followed by one `argmax`. NumPy does the whole sweep over every state and action in a single expression.

A custom checker compares `V` with `rtol=1e-9`, `atol=1e-9`, so you must stop at **exactly** the iterate the spec describes. It then checks that `policy` is an integer array and that each entry is the lowest-index action within `1e-9` of the best Q value.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `P` | `(S, A, S)` | `P[s, a, s']`, transition probabilities | `P @ V` sums over the last axis, `s'` |
| `R` | `(S, A)` | expected immediate reward | added to the discounted lookahead |
| `gamma` | float in `[0, 1)` | discount factor | weights future value |
| `tol` | float | stopping threshold | `max |V_new - V| < tol` |
| return | `(S,)` float, `(S,)` int | `V, policy` | values and the greedy action per state |

The details that are easy to miss:

- **Synchronous update.** Every `V_{k+1}(s)` uses only `V_k`. Overwriting `V[s]` mid-sweep (Gauss-Seidel) converges too, but to a different iterate when you stop.
- **Return `V_new`, not `V`.** When the test passes, the answer is the iterate you just computed.
- **The sum is over the next state**, the **last** axis of `P`. Summing over the first axis means "probability of coming **from** `s`", which is meaningless here.
- **The policy needs the lookahead.** `argmax R` picks the best immediate reward and ignores where you end up.

## 3. The math

**Bellman optimality.** The optimal value $V^*$ satisfies

$$V^*(s) = \max_a \Big[R(s, a) + \gamma \sum_{s'} P(s, a, s')\, V^*(s')\Big].$$

Write the right-hand side as an operator $T$: $(TV)(s) = \max_a Q_V(s, a)$ with $Q_V = R + \gamma P V$. Value iteration is $V_{k+1} = T V_k$ from $V_0 = 0$.

**Shapes of $PV$.** For each $(s, a)$, $(PV)(s, a) = \sum_{s'} P(s, a, s') V(s')$. In NumPy, `P @ V` with `P` of shape `(S, A, S)` and `V` of shape `(S,)` treats `V` as a vector and contracts it with the last axis of `P`, giving `(S, A)`, the same shape as `R`.

**Why it converges: $T$ is a $\gamma$-contraction.** Take any two value vectors $U, V$ and a state $s$. For every action,

$$|Q_U(s, a) - Q_V(s, a)| = \gamma\,\Big|\sum_{s'} P(s, a, s')\big(U(s') - V(s')\big)\Big| \le \gamma \sum_{s'} P(s, a, s')\,\lVert U - V \rVert_\infty = \gamma \lVert U - V\rVert_\infty,$$

since the $P(s, a, \cdot)$ are non-negative and sum to 1. The max of two functions can't differ by more than the largest pointwise difference, $|\max_a f(a) - \max_a g(a)| \le \max_a |f(a) - g(a)|$, so

$$\lVert TU - TV\rVert_\infty \le \gamma\, \lVert U - V\rVert_\infty.$$

By the Banach fixed-point theorem, $T$ has exactly one fixed point $V^*$, and $\lVert V_k - V^*\rVert_\infty \le \gamma^k \lVert V_0 - V^*\rVert_\infty$: the error shrinks by at least a factor $\gamma$ per sweep.

**What the stopping rule guarantees.** If $\lVert V_{k+1} - V_k\rVert_\infty < \text{tol}$, then using the triangle inequality and the contraction,

$$\lVert V_{k+1} - V^*\rVert_\infty \le \frac{\gamma}{1 - \gamma}\, \lVert V_{k+1} - V_k\rVert_\infty < \frac{\gamma}{1 - \gamma}\,\text{tol}.$$

At $\gamma = 0.99$ that factor is 99, so a small step doesn't mean a small error.

**The policy.** $\pi(s) = \arg\max_a Q_V(s, a)$ with the final $V$. If $V$ is close enough to $V^*$ that no action's Q value crosses another's, this is an optimal policy.

## 4. Trace an example by hand

**Example 1:** two states, `gamma = 0.5`, `tol = 1e-6`. Action 0 always goes to state 0, action 1 to state 1. `R = [[0, 1], [2, 0]]`.

| k | `V_k` | `Q_k = R + 0.5 · P V_k` | `V_{k+1}` |
|---|---|---|---|
| 0 | `[0, 0]` | `[[0, 1], [2, 0]]` | `[1, 2]` |
| 1 | `[1, 2]` | `[[0.5, 2], [2.5, 1]]` | `[2, 2.5]` |
| 2 | `[2, 2.5]` | `[[1, 2.25], [3, 1.25]]` | `[2.25, 3]` |
| 3 | `[2.25, 3]` | `[[1.125, 2.5], [3.125, 1.5]]` | `[2.5, 3.125]` |

The best plan alternates: from state 0 take action 1 (reward 1, go to state 1), from state 1 take action 0 (reward 2, go to state 0). The fixed point solves $V_0 = 1 + 0.5 V_1$, $V_1 = 2 + 0.5 V_0$, so $V_0 = 8/3$, $V_1 = 10/3$. The run takes 22 sweeps to get a step below `1e-6`, and the policy is `[1, 0]`.

**Example 2** is a 5-state chain with `gamma = 0.9`. Action 1 moves right; moving right from state 3 pays 1 and lands in absorbing state 4.

| sweep | `V_{k+1}` | max change |
|---|---|---|
| 1 | `[0, 0, 0, 1, 0]` | `1` |
| 2 | `[0, 0, 0.9, 1, 0]` | `0.9` |
| 3 | `[0, 0.81, 0.9, 1, 0]` | `0.81` |
| 4 | `[0.729, 0.81, 0.9, 1, 0]` | `0.729` |
| 5 | unchanged | `0`: stop |

Value flows backward one state per sweep. In state 4 both actions give `Q = 0`, so the policy picks action 0: `[1, 1, 1, 1, 0]`. Here the policy from `R` alone would be `[0, 0, 0, 1, 0]`, because only state 3 has an immediate reward.

**The hidden case "loose tolerance"** uses `gamma = 0.95` and `tol = 1e-2`, and stops after 75 sweeps with `V[0] = 9.506482`. Returning the previous iterate gives `9.49696`; Gauss-Seidel stops at `9.58399`. With a tight tolerance those would round to the same number, which is why this case exists.

## 5. Plan before you code

```
V = zeros(S)
loop:
    Q = R + gamma * (P @ V)          # (S, A)
    V_new = max of Q over actions    # (S,)
    if max |V_new - V| < tol: V = V_new; stop
    V = V_new
Q = R + gamma * (P @ V)              # (S, A), from the final V
policy = argmax of Q over actions    # (S,), lowest index on ties
```

| line | shapes | broadcasting |
|---|---|---|
| `P @ V` | `(S, A, S) @ (S,)` | contracts the last axis: `(S, A)` |
| `R + gamma * (...)` | `(S, A) + (S, A)` | none |
| `Q.max(axis=1)` | `(S, A) -> (S,)` | reduces over actions |

## 6. Build it one piece at a time

**Step 1: one synchronous sweep.**

```python
Q = R + gamma * (P @ V)        # (S, A): reward plus discounted expected next value
V_new = Q.max(axis=1)          # (S,): best action per state
```

Both lines read only the old `V`, so every state's update uses the same snapshot. That's the definition of synchronous.

**Step 2: the stopping test.**

```python
if np.max(np.abs(V_new - V)) < tol:
    V = V_new
    break
V = V_new
```

Assign `V = V_new` on **both** paths. On the stopping path, forgetting it returns `V_k` instead of `V_{k+1}`.

**Step 3: the greedy policy.**

```python
Q = R + gamma * (P @ V)
policy = np.argmax(Q, axis=1)   # (S,), int, first maximum on ties
```

`np.argmax` returns an integer array and picks the first of equal maxima. The checker also accepts any action within `1e-9` of the max being resolved to the lowest index, so tiny round-off differences in `Q` don't matter.

## 7. Full solution

```python
# NumPy for the batched Bellman backup
import numpy as np


# P: (S, A, S) transitions, R: (S, A) rewards; returns (V (S,), policy (S,))
def value_iteration(P: np.ndarray, R: np.ndarray, gamma: float, tol: float = 1e-8) -> tuple:
    V = np.zeros(P.shape[0])  # V_0 = 0 for every state
    # keep applying the Bellman operator until the values stop moving
    while True:
        # (S, A): P @ V sums over the next state s' (last axis), all states and actions at once
        Q = R + gamma * (P @ V)
        V_new = Q.max(axis=1)  # (S,) best action value per state, from the old V only
        # largest change across states is below tol: this iterate is the answer
        if np.max(np.abs(V_new - V)) < tol:
            V = V_new  # return V_{k+1}, the iterate that passed the test
            break  # converged
        V = V_new  # synchronous: the whole new vector replaces the old one
    # (S, A) action values under the final V, for the greedy policy
    Q = R + gamma * (P @ V)
    # greedy action per state; argmax takes the lowest index on ties
    return V, np.argmax(Q, axis=1)
```

## 8. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `V ≈ [2.6667, 3.3333]`, policy `[1, 0]`, 22 sweeps | convergence to a cycle's value; returning `V_new` |
| Example 2 | `V = [0.729, 0.81, 0.9, 1, 0]`, policy `[1, 1, 1, 1, 0]` | lookahead in the policy; the tie in state 4 |
| gamma = 0 | stops after 2 sweeps, `V = max_a R` | no future value at all |
| tied actions | action 2 duplicates action 0; policy `[1, 0, 0, 1, 1, 1]` | ties go to the lower index |
| loose tolerance | `V[0] = 9.506482` after 75 sweeps | the exact stopping iterate, synchronous updates |
| single action | `A = 1`, policy all 0 | value iteration is just policy evaluation |
| single state | `V = [4]`, policy `[1]` | `V = 2 + 0.5 V` |
| long horizon chain | `gamma = 0.99`, `V[0] = 0.904382` | slow discounting over 12 states |
| sparse random mdp | `S = 40`, `A = 5`, 156 sweeps | many zero transitions, larger size |

## 9. Complexity

One sweep is a contraction of an $S \times A \times S$ tensor, so $O(S^2 A)$ time, plus $O(SA)$ memory for $Q$. The error falls like $\gamma^k$, so reaching tolerance $\epsilon$ from an initial error $\Delta$ needs about $\log(\epsilon / \Delta) / \log \gamma \approx \frac{1}{1 - \gamma} \ln \frac{\Delta}{\epsilon}$ sweeps. That's why "sparse random mdp" at `gamma = 0.9` takes 156 sweeps, while the deterministic chains stop as soon as value has reached every state.

Dense `P` stops being practical beyond tens of thousands of states. Real problems either store sparse transitions (each state reaches only a few successors), or give up on enumerating states and learn $Q$ from samples with function approximation, which is where Q-learning and deep RL come in.

## 10. If you got Wrong Answer

- **`V` differs in the last digits only, in Example 1, "loose tolerance", "single action" and "sparse random mdp".** You returned the previous iterate after the test passed (`wrong_return_old_v.py`). The message shows `2.66667` against `2.66667`: they differ below the displayed precision but above `1e-9`.
- **Same symptoms, but the values are a little high in "loose tolerance" (`9.58399` instead of `9.50648`).** You updated `V[s]` in place while sweeping (`wrong_gauss_seidel.py`).
- **`V` is completely wrong (Example 2 gives `V[0] = 0` instead of `0.729`).** You summed over the first axis of `P` (`wrong_transition_axis.py`).
- **`V` is right but the policy isn't (Example 2 gives `policy[0] = 0`).** You took `argmax R` without the lookahead (`wrong_policy_from_r.py`).
- **The policy is rejected as not an integer array.** Return `np.argmax(...)` directly, not a float conversion.

## 11. Follow-ups an interviewer might ask

- *How does policy iteration differ?* It alternates full policy evaluation (solving a linear system) with greedy improvement. It needs fewer iterations, each costlier, and terminates exactly in a finite number of steps.
- *What if you don't know `P` and `R`?* Sample transitions and update a Q table toward the same Bellman target (problem 89, q-learning-update).
- *Why discount at all?* It keeps infinite sums finite and makes $T$ a contraction. Without it you need terminal states or average-reward formulations.
- *How do you speed it up?* Gauss-Seidel or prioritized sweeping (update the states whose values changed most), or stop when the greedy policy stops changing rather than when $V$ does.
- *How does this connect to advantages in policy-gradient methods?* $A(s, a) = Q(s, a) - V(s)$ measures how much better an action is than average; GAE estimates it from sampled rewards (problem 90, gae-advantages).
