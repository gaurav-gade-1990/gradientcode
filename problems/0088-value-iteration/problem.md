Solve a finite MDP with **value iteration**.

`P[s, a, s']` is the probability of moving to state `s'` after taking action `a` in state `s`. `R[s, a]` is the expected immediate reward. Start from $V_0 = 0$ and apply the Bellman optimality backup to **all states at once** (a synchronous update, computed only from the previous $V$):

$$
Q_k(s, a) = R(s, a) + \gamma\sum_{s'} P(s, a, s')\,V_k(s'), \qquad V_{k+1}(s) = \max_a Q_k(s, a)
$$

Stop at the first $k$ where $\max_s |V_{k+1}(s) - V_k(s)| < \texttt{tol}$, and take $V = V_{k+1}$.

Then compute the greedy policy from that $V$: $\pi(s) = \arg\max_a \bigl[R(s,a) + \gamma\sum_{s'}P(s,a,s')V(s')\bigr]$. If several actions tie, pick the lowest index.

Return a tuple `(V, policy)`: `V` is a float array of shape `(S,)` and `policy` is an integer array of shape `(S,)`.

**Constraints**

- `P` has shape `(S, A, S)`, and each `P[s, a]` sums to `1`
- `R` has shape `(S, A)`
- `1 <= S <= 50`, `1 <= A <= 6`
- `0 <= gamma < 1`, `tol > 0`
