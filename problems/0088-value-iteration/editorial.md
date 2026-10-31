## Approach

The Bellman optimality operator $T$ is a $\gamma$-contraction in the max norm. Applying it over and over from any start converges to the unique fixed point $V^*$, and the error shrinks by a factor of $\gamma$ each sweep.

With `P` of shape `(S, A, S)`, `P @ V` contracts the last axis and gives the expected next value for every `(s, a)` pair in one call.

$$
Q = R + \gamma\,P V, \qquad V \leftarrow \max_a Q
$$

```python
V = np.zeros(P.shape[0])
while True:
    V_new = (R + gamma * (P @ V)).max(axis=1)
    if np.max(np.abs(V_new - V)) < tol:
        V = V_new
        break
    V = V_new
policy = np.argmax(R + gamma * (P @ V), axis=1)
```

Once $V$ is close to $V^*$, the greedy policy with respect to it is optimal, provided the gap between the best and second-best action values is larger than the error.

## Common mistakes

- **Gauss-Seidel sweeps.** Overwriting `V[s]` during a sweep also converges, often faster, but it stops at a different iterate. The spec asks for synchronous updates.
- **Returning the previous iterate.** When the stopping test passes, the answer is `V_new`, not `V`.
- **Contracting the wrong axis.** The sum is over the **next** state $s'$, the last axis of `P`.
- **Policy from `R` alone.** The greedy policy must look ahead through $\gamma P V$.

## Complexity

- **Time:** $O(S^2 A)$ per sweep. The number of sweeps is about $\log(\text{tol}) / \log\gamma$, which grows like $1/(1 - \gamma)$.
- **Space:** $O(SA)$ for $Q$, on top of the $O(S^2 A)$ input.
