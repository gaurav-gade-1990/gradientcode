Implement the forward pass of a sparse **Mixture-of-Experts** layer with top-k routing, plus the Switch Transformer **load-balancing loss** (Fedus et al., 2021).

You get `T` tokens `x` of shape `(T, d)`, a router weight `W_router` of shape `(d, E)`, and `E` experts. Expert $e$ is the linear map $x \mapsto x\,\texttt{experts[e]}$, where `experts` has shape `(E, d, d_out)`.

**Routing.** For each token $t$:

1. $p_t = \operatorname{softmax}(x_t W_{router})$ over all $E$ experts, computed stably.
2. Choose the $k$ experts with the largest $p_{t,e}$, in **descending order of probability**. Ties go to the **lower expert index**.
3. Renormalize the chosen probabilities into gates: $g_{t,i} = p_{t,e_i} / \sum_{i'=1}^{k} p_{t,e_{i'}}$.
4. $y_t = \sum_{i=1}^{k} g_{t,i}\; x_t\,\texttt{experts}[e_i]$.

**Load-balancing loss.**

$$
f_e = \frac{\#\{(t, i) : e_{t,i} = e\}}{T\,k}, \qquad
P_e = \frac{1}{T}\sum_{t=1}^{T} p_{t,e}, \qquad
\mathcal{L}_{aux} = E \sum_{e=1}^{E} f_e\, P_e
$$

$f_e$ is the fraction of the $T k$ routing slots sent to expert $e$. $P_e$ is the mean router probability over the **full** softmax, not just the chosen experts. With perfectly uniform routing, $\mathcal{L}_{aux} = 1$.

Return a tuple `(y, expert_idx, gates, aux_loss)`:

- `y`: shape `(T, d_out)`
- `expert_idx`: int array of shape `(T, k)`, the chosen experts in the order above
- `gates`: shape `(T, k)`, aligned with `expert_idx`
- `aux_loss`: a Python float

**Constraints**

- `1 <= T <= 64`, `1 <= d, d_out <= 32`
- `1 <= k <= E <= 16`
