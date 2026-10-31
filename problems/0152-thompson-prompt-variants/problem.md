Your onboarding assistant has several system-prompt variants. Instead of a fixed A/B split, the prompt service routes each new conversation with **Beta-Bernoulli Thompson sampling** on whether the user finished onboarding. New variants launch mid-flight, and a variant derived from an existing prompt starts with a **warm-start** prior, so it doesn't spend its first hundred conversations proving it isn't broken.

Implement `run_thompson(variants, requests, sample_beta, warm_weight)`.

- `variants` is a list of `{"id", "launch_at", "warm_start_from"}`. `launch_at` is the index of the first request the variant may serve. `warm_start_from` is the id of an earlier variant, or `None`.
- `requests` is a list of `{"request_id", "outcomes"}`. `outcomes[variant_id]` is `1` if this user would finish onboarding when served that variant, else `0` (the simulator knows the counterfactuals, but your bandit may only learn the outcome of the variant it served).
- `sample_beta(a, b)` returns one draw from Beta(a, b). It is the **only** randomness. The judge records every call.
- `warm_weight` is a non-negative integer: the pseudo-count budget of a warm start.

**Priors.** A variant with `warm_start_from = None` starts at `(a, b) = (1, 1)`. A warm-started variant computes its prior at the moment it launches, from its parent's current posterior `(a_p, b_p)`:

$$
s = \left\lfloor \frac{\text{warm\_weight}\cdot a_p}{a_p + b_p} \right\rfloor, \qquad (a, b) = (1 + s,\ 1 + \text{warm\_weight} - s)
$$

**Each request `i`**, in order:

1. Activate the variants with `launch_at == i`, in list order, computing their priors.
2. For every **active** variant (`launch_at <= i`), in list order, call `sample_beta(a, b)` exactly once.
3. Serve the variant with the largest draw. Ties go to the earlier variant in the list.
4. Observe `r = outcomes[served]` and update only the served variant: `a += r`, `b += 1 - r`.

After the last request, the **leader** is the variant with the highest posterior mean `a / (a + b)` among the variants that served at least one request, with ties to the earlier variant. A warm-started variant that never served has only borrowed evidence, so it can't lead. Compare exactly, by cross-multiplying.

Return:

```
{
  "choices":     [variant id served for each request],
  "allocations": {variant_id: number of requests served},
  "priors":      {variant_id: [a0, b0]},
  "posteriors":  {variant_id: [a, b]},
  "reward":      total r over all requests,
  "leader":      variant_id
}
```

**Constraints**

- `1 <= len(variants) <= 5`. The first variant has `launch_at = 0`, and every `launch_at < len(requests)`.
- A `warm_start_from` parent appears earlier in the list with a strictly smaller `launch_at`.
- `1 <= len(requests) <= 120`, `0 <= warm_weight <= 50`
- Don't import `random`. Use only `sample_beta`.
