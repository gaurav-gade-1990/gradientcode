## Approach

Thompson sampling serves each arm with the probability that it's the best one, given what you've seen. Draw once from each posterior and serve the argmax. With Bernoulli rewards and a Beta prior the update is just counting:

$$
\theta_v \sim \text{Beta}(a_v, b_v), \quad \text{serve } \arg\max_v \theta_v, \quad a \mathrel{+}= r,\ b \mathrel{+}= 1 - r
$$

The only production twist is **warm starts**. A variant forked from a prompt with a 75% success rate shouldn't start at Beta(1, 1), where a 10% prompt and a 90% prompt look alike. It also shouldn't inherit the parent's thousands of observations. Give it a fixed pseudo-count budget at the parent's mean:

```python
s = (warm_weight * a_p) // (a_p + b_p)
prior = [1 + s, 1 + warm_weight - s]
```

Then the loop is: activate, draw for every active arm in list order, serve, and update only the served arm. The leader comparison uses `a1 * (a2 + b2) > a2 * (a1 + b1)`, so equal means really tie.

## Common mistakes

- **Greedy on the posterior mean.** No exploration. One early failure on the better prompt can starve it for the rest of the run.
- **Copying the parent's posterior.** The new prompt starts with the parent's full confidence, so it takes forever to move off the parent's rate, which defeats the point of testing it.
- **No warm start.** It works, but it burns traffic sending users to a variant you already have good evidence about.
- **Counterfactual updates.** The simulator knows what every prompt would have done, and production never does. Updating unserved arms makes the simulation look far better than reality.
- **Sampling variants before launch.** That's how a prompt still in legal review ends up serving users.

## Production notes

- This is the bandit behind adaptive experiments in Optimizely and Statsig (their "multi-armed bandit" mode) and in many prompt-routing services. Rewards are often delayed (onboarding finishes hours later), so production systems update in batches from a reward log instead of per request.
- Bandits minimize regret, but they don't give you a clean effect estimate. If you need to report "the checklist prompt lifts completion by 4 points", run a fixed-split test (`ab-test-significance`) or use inverse-propensity weighting on the logged serve probabilities.
- Log the serve probability (or the draws) with each choice. Offline policy evaluation and audits both need it.
- Add guardrails outside the bandit. A variant that trips a safety or cost threshold is removed from the active set, no matter what its conversion posterior says. `feature-flag-rollout` is the kill switch.
