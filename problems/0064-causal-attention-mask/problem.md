Build the **additive causal mask** used in decoder self-attention, including the case where the queries are the last few positions of a longer sequence, as happens with a KV cache.

The keys cover absolute positions $0, 1, \dots, T_k - 1$. Query row $i$ sits at absolute position $i + \text{offset}$. A query may attend to a key at the same position or earlier:

$$
M_{ij} = \begin{cases} 0 & \text{if } j \le i + \text{offset} \\ -\infty & \text{otherwise} \end{cases}
$$

The mask is added to the attention scores before the softmax. With `offset = 0` and `T_q = T_k` it is the usual lower-triangular mask. When you decode with a cache of $P$ past tokens and feed $T_q$ new ones, `T_k = P + T_q` and `offset = P`.

Return a float array of shape `(T_q, T_k)` containing only `0.0` and `-inf`. Use `-np.inf`, not a large negative number.

**Constraints**

- `1 <= T_q <= 64`, `1 <= T_k <= 64`
- `0 <= offset`. The offset may be larger than `T_k - T_q`. Positions past the end of the keys are simply visible.
