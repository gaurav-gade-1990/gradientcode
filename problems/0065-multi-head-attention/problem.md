Implement **multi-head self-attention** for a batch of sequences.

Let $h$ = `num_heads` and $d_{head} = d_{model} / h$. Vectors are rows, and there are no biases.

1. **Project.** $Q = x W_q$, $K = x W_k$, $V = x W_v$, each of shape `(B, T, d_model)`.
2. **Split heads.** Head $j$ owns the contiguous columns `j*d_head : (j+1)*d_head` of $Q$, $K$ and $V$.
3. **Attend.** For each batch element and head:
$$
O_j = \operatorname{softmax}\left(\frac{Q_j K_j^\top}{\sqrt{d_{head}}} + M\right) V_j
$$
4. **Merge.** Concatenate $O_0, \dots, O_{h-1}$ along the feature axis in head order, giving `(B, T, d_model)`, and multiply by $W_o$.

Inputs:

- `x` has shape `(B, T, d_model)`.
- `W_q`, `W_k`, `W_v`, `W_o` each have shape `(d_model, d_model)`. They are applied as `x @ W`.
- `mask` is `None` or a boolean `(T, T)` array shared by every batch element and head. `True` means *keep* the pair (query row, key column). Dropped pairs get weight exactly `0`.

Return the output of shape `(B, T, d_model)`. Use a numerically stable softmax.

**Constraints**

- `1 <= B <= 4`, `1 <= T <= 16`, `1 <= num_heads <= 8`
- `d_model` is divisible by `num_heads`, and `d_model <= 32`
- If `mask` is given, every query row keeps at least one key
