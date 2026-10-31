## Approach

The draft model is cheap but wrong. The target model is right but expensive per call, and it can score $K$ proposed tokens in a single forward pass. Speculative decoding uses **rejection sampling** to keep only what the target would have produced anyway.

For draft token $x \sim q$, accept with probability $\min(1, p(x)/q(x))$. Tokens the draft over-proposes ($q > p$) get thinned out. Tokens it under-proposes ($p > q$) are always kept, but they still come up too rarely. The residual makes up the difference: on rejection, sample from $\max(0, p - q)$, normalized. Together:

$$
P(\text{output} = v) = \min(p(v), q(v)) + \Big(1 - \sum_w \min(p(w), q(w))\Big)\frac{\max(0, p(v) - q(v))}{\sum_w \max(0, p(w) - q(w))} = p(v)
$$

because $1 - \sum_w \min(p, q) = \sum_w \max(0, p - q)$.

```python
for i in range(K):
    x = draft_tokens[i]
    if u_accept[i] < p[i, x] / q[i, x]:
        tokens.append(x)
        continue
    tokens.append(sample(np.maximum(0.0, p[i] - q[i]), u_sample[i]))
    return np.array(tokens), i
tokens.append(sample(p[K], u_sample[K]))      # all accepted: free bonus token
return np.array(tokens), K
```

`u < p/q` with $u \in [0, 1)$ already means "accept with probability $\min(1, p/q)$", so no explicit `min` is needed.

After a rejection, every later draft was conditioned on a token that is no longer in the sequence, so they must be discarded. When everything is accepted, the target's pass already computed `p[K]`, and the bonus token costs nothing. Each verification step therefore yields between 1 and $K + 1$ tokens.

## Common mistakes

- **Resampling from $p$.** That double-counts the mass already accepted, and the output is no longer distributed as $p$.
- **No bonus token.** The output is correct but you waste the target's last row.
- **Continuing after a rejection.** Later drafts depend on the rejected prefix.
- **Using $q/p$.** Inverting the ratio favors exactly the tokens the draft over-proposes.

## Complexity

- **Time:** $O(KV)$ in the worst case: at most one residual and one cumulative sum of length $V$.
- **Space:** $O(V)$ for the residual.
