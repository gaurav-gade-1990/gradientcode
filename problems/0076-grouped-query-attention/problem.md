Implement causal **grouped-query attention** (GQA, Ainslie et al., 2023), as used in LLaMA 2 70B and Mistral.

There are `n_q` query heads but only `n_kv` key/value heads, with `n_q` a multiple of `n_kv`. Let $g = n_q / n_{kv}$. Query heads are split into `n_kv` **consecutive** groups of size $g$, and every head in a group shares one K/V head:

$$
\text{kv}(h) = \left\lfloor h / g \right\rfloor
$$

This is `repeat_interleave` semantics: with `n_q = 4, n_kv = 2`, query heads `0, 1` use K/V head `0` and heads `2, 3` use K/V head `1`.

For each batch element $b$, query head $h$ and query position $i$:

$$
s_{ij} = \frac{q_{b,h,i} \cdot k_{b,\text{kv}(h),j}}{\sqrt{d}}, \qquad
o_{b,h,i} = \sum_{j \le i} \operatorname{softmax}_j(s_{ij})\, v_{b,\text{kv}(h),j}
$$

The attention is **causal**: position $i$ attends to positions $j \le i$, including itself. Use a numerically stable softmax.

Return an array of shape `(B, n_q, T, d)`.

**Constraints**

- `q` has shape `(B, n_q, T, d)`; `k` and `v` have shape `(B, n_kv, T, d)`
- `n_q % n_kv == 0`, `1 <= n_kv <= n_q <= 16`
- `1 <= T <= 64`, `1 <= d <= 64`
