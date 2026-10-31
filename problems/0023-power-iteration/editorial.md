## Approach

Write $v_0 = \sum_i c_i u_i$ in the eigenbasis of $A$. Then

$$
A^t v_0 = \sum_i c_i \lambda_i^t u_i = \lambda_1^t \Big( c_1 u_1 + \sum_{i>1} c_i (\lambda_i/\lambda_1)^t u_i \Big).
$$

Every other term shrinks like $|\lambda_2/\lambda_1|^t$, so the direction converges to $\pm u_1$. Normalizing after each multiply keeps the magnitude at 1. Without that, $|\lambda_1|^t$ overflows quickly: $1000^{103}$ is already `inf`.

```python
def power_iteration(A, v0, n_iters):
    v = v0 / np.linalg.norm(v0)
    for _ in range(n_iters):
        w = A @ v
        v = w / np.linalg.norm(w)
    return float(v @ A @ v), v
```

### Why the Rayleigh quotient?

$\lambda = v^\top A v$ is accurate to second order: an $O(\epsilon)$ error in $v$ gives an $O(\epsilon^2)$ error in $\lambda$. It also keeps the sign. If $\lambda_1 < 0$, the iterate flips sign every step and $\lVert Av \rVert = |\lambda_1|$, but $v^\top A v = \lambda_1$.

## Common mistakes

- **$\lVert A v \rVert$ as the eigenvalue.** It's wrong whenever the dominant eigenvalue is negative.
- **Normalizing only at the end.** Mathematically it's the same direction, but in floating point it overflows to `inf` and then `nan`.
- **Not normalizing `v0`.** With zero iterations, the returned vector isn't unit length.

## Complexity

- **Time:** $O(T d^2)$ for $T$ iterations. Convergence takes about $\log(1/\epsilon) / \log|\lambda_1/\lambda_2|$ iterations, which is slow when the gap is small.
- **Space:** $O(d)$ beyond $A$.
