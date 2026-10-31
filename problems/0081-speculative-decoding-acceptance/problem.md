Implement the verification step of **speculative decoding** (Leviathan et al., 2023; Chen et al., 2023).

A small draft model has proposed `K` tokens `draft_tokens`. At draft position $i$ it sampled $x_i$ from its distribution $q_i$ = `q[i]`. The large target model then scored all positions in one forward pass, giving $p_i$ = `p[i]` for $i = 0, \dots, K$. The extra row `p[K]` is the target's distribution for the token after the last draft.

Process the draft positions in order $i = 0, 1, \dots, K-1$:

1. **Accept** $x_i$ if `u_accept[i]` $< \dfrac{p_i(x_i)}{q_i(x_i)}$. Append $x_i$ to the output and move on.
2. Otherwise **reject**. Sample a replacement token from the residual distribution
   $$
   r(v) \propto \max\big(0,\ p_i(v) - q_i(v)\big)
   $$
   using `u_sample[i]`, append it, and **stop**. The remaining draft tokens are discarded.

If all $K$ drafts are accepted, sample one **bonus** token from $p_K$ using `u_sample[K]` and append it.

**Sampling rule.** To sample from non-negative weights $w$ (unnormalized is fine) with a uniform $u$: let $c = \operatorname{cumsum}(w)$ and return the smallest index $j$ with $c_j > u \cdot c_{V-1}$. In NumPy that is `np.searchsorted(c, u * c[-1], side="right")`.

This procedure makes every output token distributed exactly as if it had been sampled from the target model.

Return a tuple `(tokens, num_accepted)`:

- `tokens`: a 1-D int array of length `num_accepted + 1`: the accepted drafts followed by the one resampled or bonus token
- `num_accepted`: an int, the number of draft tokens accepted

**Constraints**

- `draft_tokens` is an int array of shape `(K,)`, `1 <= K <= 16`
- `q` has shape `(K, V)`, `p` has shape `(K + 1, V)`, `2 <= V <= 100`; every row is a probability distribution
- `q[i, draft_tokens[i]] > 0` (the draft really could have sampled it)
- `u_accept` has shape `(K,)` and `u_sample` has shape `(K + 1,)`, all in `[0, 1)`
- Whenever a rejection is possible, the residual has positive mass
