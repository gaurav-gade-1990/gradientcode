## Approach

A MoE layer replaces one big FFN with $E$ experts and lets a learned router send each token to only $k$ of them. Compute per token grows with $k$, while parameters grow with $E$.

**Route.** Softmax the router logits, take the top $k$, and renormalize so the chosen gates sum to 1. (Mixtral does this. Renormalizing the top-k probabilities equals a softmax over the top-k logits.)

```python
p = softmax(x @ W_router)                               # (T, E)
idx = np.argsort(-p, axis=1, kind="stable")[:, :k]       # ties -> lower index
top = np.take_along_axis(p, idx, axis=1)
gates = top / top.sum(axis=1, keepdims=True)
```

**Combine.** Each token's output is the gate-weighted sum of its chosen experts' outputs. Here every expert runs on every token for simplicity. A real kernel gathers the tokens per expert instead.

```python
out = np.einsum("td,edo->teo", x, experts)
y = (gates[:, :, None] * np.take_along_axis(out, idx[:, :, None], axis=1)).sum(1)
```

**Balance.** Without a penalty the router collapses onto a few experts. The Switch loss multiplies the fraction of slots each expert receives ($f_e$, not differentiable) by its mean router probability ($P_e$, differentiable), so gradients push probability away from overloaded experts:

$$
\mathcal{L}_{aux} = E \sum_e f_e P_e
$$

## Common mistakes

- **Not renormalizing.** The chosen gates no longer sum to 1, so the output is scaled down.
- **Tie order.** `argsort(p)[:, ::-1]` reverses ties too, so it prefers the higher index.
- **$P_e$ from the gates.** $P_e$ uses the full softmax over all experts, including the ones a token didn't pick.
- **Unstable softmax.** Large router logits overflow `exp`.

## Complexity

- **Time:** $O(T d E)$ for routing and $O(T E \log E)$ to sort. Real MoE runs only $O(T k\, d\, d_{out})$ of expert work; this dense reference does $O(T E\, d\, d_{out})$.
- **Space:** $O(T E)$ for the probabilities.
