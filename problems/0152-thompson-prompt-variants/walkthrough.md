## 1. What the problem is really asking

You have a few system-prompt variants and you want to send more users to the one that works, while still learning about the others. A fixed 50/50 split wastes half your traffic on a loser for the whole test. **Thompson sampling** shifts traffic as evidence comes in: for every request, draw a plausible success rate for each variant from its posterior, and serve the variant with the highest draw. Uncertain variants sometimes draw high and get explored. Confident winners usually draw highest and get exploited.

Under the story, this is **a per-request loop with a Beta posterior per variant**:

- each variant holds two integers `(a, b)`, its Beta posterior: roughly `a - 1` successes and `b - 1` failures plus the prior;
- each request: activate new variants, draw once per active variant, serve the argmax, update only the served one;
- two twists: variants launch mid-flight, and a derived variant can start from a **warm-start** prior borrowed from its parent.

All randomness comes through `sample_beta`, and the driver records every call's `(a, b)`. So the judge checks not just which variant you served, but how many draws you made, in what order, with which parameters. One extra or missing draw shifts every later draw and changes everything after it.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `variants` | `{id, launch_at, warm_start_from}` in a fixed list order | list order sets draw order and breaks ties |
| `launch_at` | first request index the variant may serve | activate when `i == launch_at`; draw when `launch_at <= i` |
| `warm_start_from` | a parent id, or `None` | the prior is computed from the parent's posterior *at launch* |
| `requests[i]["outcomes"]` | what every variant would have done | read only `outcomes[served]` |
| `sample_beta(a, b)` | one Beta draw; the only randomness | exactly one call per active variant per request |
| `warm_weight` | pseudo-count budget for a warm start | the `s` formula |

Three details are easy to miss:

- **One draw per active variant, even if only one is active.** In Example 3 there's a single variant, and it still gets one `sample_beta` call per request.
- **The simulator knows counterfactuals; you must not use them.** Production only learns the outcome of the prompt the user saw.
- **The driver's `sample_beta` maps a fixed uniform through the Beta quantile**, so equal `(a, b)` and equal uniforms give bit-identical draws. Ties really happen, and they go to the earlier variant.

## 3. The math

A Beta(a, b) distribution over a success rate $p$ has density proportional to $p^{a-1}(1-p)^{b-1}$ and mean $a/(a+b)$. It's the conjugate prior for a Bernoulli outcome: if the prior is Beta(a, b) and you observe one outcome $r \in \{0, 1\}$, the posterior is

$$
p^{a-1}(1-p)^{b-1}\cdot p^{r}(1-p)^{1-r} = p^{(a+r)-1}(1-p)^{(b+1-r)-1}
$$

which is Beta(a + r, b + 1 - r). That's the whole update: `a += r`, `b += 1 - r`. Beta(1, 1) is the uniform distribution, "no idea yet".

**The warm start.** A derived prompt is probably similar to its parent, but not identical. So instead of copying the parent's posterior (all of its evidence), you give it a fixed budget of `warm_weight` pseudo-observations, split in the ratio of the parent's mean:

$$
s = \left\lfloor \frac{\text{warm\_weight}\cdot a_p}{a_p + b_p} \right\rfloor, \qquad (a, b) = (1 + s,\ 1 + \text{warm\_weight} - s)
$$

The new prior has mean close to the parent's but only `warm_weight` pseudo-counts of confidence, so real traffic can move it quickly. Integer floor division keeps it exact.

## 4. Trace Example 1 by hand

Two variants launched at 0, `warm_weight = 0`, uniforms `[0.9, 0.2, 0.3, 0.7, 0.5, 0.5]`. For Beta(1, 1) the quantile is the uniform itself. For Beta(2, 1) the CDF is $x^2$, so the quantile is $\sqrt u$.

| request | concise (a, b) → draw | friendly (a, b) → draw | served | outcome | update |
|---|---|---|---|---|---|
| conv-001 | (1, 1) → 0.9 | (1, 1) → 0.2 | concise | 1 | concise (2, 1) |
| conv-002 | (2, 1) → √0.3 = 0.5477 | (1, 1) → 0.7 | friendly | 1 | friendly (2, 1) |
| conv-003 | (2, 1) → √0.5 = 0.7071 | (2, 1) → √0.5 = 0.7071 | concise (tie, earlier) | 1 | concise (3, 1) |

The recorded calls are `[[1,1],[1,1],[2,1],[1,1],[2,1],[2,1]]`. The reward is 3, the allocations are 2 and 1, and the leader is concise: its mean 3/4 beats friendly's 2/3.

**Example 2 shows the launch and the warm start.** Only `v1` is active for requests 0 and 1. It gets one draw each, and both succeed: `(3, 1)`. At request index 2, `v1-short` launches with `warm_weight = 10`: `s = (10 · 3) // 4 = 7`, prior `(8, 4)`. The draws are Beta(3, 1) at 0.6 = 0.8434 and Beta(8, 4) at 0.1 = 0.4892, so v1 serves and fails: `(3, 2)`. Now `v1-short` has the higher mean, 8/12 against v1's 3/5, but it never served, so its confidence is all borrowed. The leader is `v1`.

## 5. Key idea: only the served variant learns

The simulator's `outcomes` dict holds what every variant would have done, so it's tempting to update all of them. That's information production never has. In Example 1, updating every arm makes friendly learn from requests it never served, and the draws on request 2 become Beta(2, 1) against Beta(1, 2): concise serves all three requests. In "three arms from cold", the counterfactual version piles 92 of 100 requests onto checklist. The real bandit sends it 81, and the difference is the cost of having to explore.

The opposite mistake is no exploration at all: serving the best posterior mean. In "three arms from cold", checklist (true rate 0.55) has an unlucky start, its mean drops below the others, and a greedy policy never comes back to it. Greedy ends with checklist served only twice, a reward of 25 against Thompson's 53, and the wrong leader (`baseline`).

## 6. Plan before you code

```
post, priors = {}, {}; alloc = {id: 0}
for i, request:
    for v in variants (list order): if launch_at == i:
        prior = (1, 1) if no parent else warm-start from post[parent]
        priors[v] = post[v] = prior
    best = None
    for v in variants (list order): if launch_at <= i:
        draw = sample_beta(*post[v]); keep it if strictly greater than best so far
    r = outcomes[best]; post[best] += (r, 1 - r); alloc[best] += 1
leader = highest a/(a+b) among variants with alloc > 0, cross-multiplied, earlier wins ties
```

| situation | what happens |
|---|---|
| not yet launched (`launch_at > i`) | no draw, no state |
| launches now, no parent | prior `(1, 1)` |
| launches now, parent given | prior from the parent's *current* posterior |
| active, not served | one draw, no update |
| served | one draw, then `a += r`, `b += 1 - r` |

## 7. Build it one piece at a time

**Step 1: activation and priors.** Compute the warm start at the moment of launch, from the parent's posterior *then*. Store a copy in `priors` so later updates don't change the reported prior:

```python
for v in variants:
    if v["launch_at"] == i:
        parent = v["warm_start_from"]
        if parent is None:
            prior = [1, 1]
        else:
            a_p, b_p = post[parent]
            s = (warm_weight * a_p) // (a_p + b_p)
            prior = [1 + s, 1 + warm_weight - s]
        priors[v["id"]] = list(prior)
        post[v["id"]] = list(prior)
```

The constraint "a parent launches strictly earlier" guarantees `post[parent]` exists. In "warm-start chain", `c` launches from `b` and `d` from `c`. `c` never serves, so its posterior at `d`'s launch is still its prior `(5, 5)`, and `d` gets `s = 8 · 5 // 10 = 4`, prior `(5, 5)`.

**Step 2: draw and pick.** Strict `>` keeps the earlier variant on a tie:

```python
best, best_draw = None, None
for v in variants:
    if v["launch_at"] <= i:
        a, b = post[v["id"]]
        draw = sample_beta(a, b)
        if best is None or draw > best_draw:
            best, best_draw = v["id"], draw
```

**Step 3: observe and update the served variant only.**

```python
r = req["outcomes"][best]
post[best][0] += r
post[best][1] += 1 - r
```

**Step 4: the leader.** Compare $a_1/(a_1+b_1) > a_2/(a_2+b_2)$ as $a_1(a_2+b_2) > a_2(a_1+b_1)$. All values are integers, so ties are exact. In "leader tie by list order", `x` and `y` both end at `(2, 1)`, and strict `>` keeps `x`.

## 8. Full solution

```python
def run_thompson(variants, requests, sample_beta, warm_weight):  # Beta-Bernoulli Thompson sampling with launches
    post, priors = {}, {}  # current (a, b) per launched variant, and the prior each started from
    alloc = {v["id"]: 0 for v in variants}  # requests served per variant, launched or not
    choices, reward = [], 0  # served variant per request, and total successes
    for i, req in enumerate(requests):  # one routing decision per conversation
        for v in variants:  # activate in list order
            if v["launch_at"] == i:  # this variant goes live now
                parent = v["warm_start_from"]  # derived from an earlier prompt, or not
                if parent is None:  # a brand-new prompt
                    prior = [1, 1]  # uniform: no evidence yet
                else:  # borrow a capped amount of the parent's evidence
                    a_p, b_p = post[parent]  # the parent's posterior at this moment
                    s = (warm_weight * a_p) // (a_p + b_p)  # pseudo-successes in the parent's ratio, integer math
                    prior = [1 + s, 1 + warm_weight - s]  # warm_weight pseudo-counts, not the parent's full history
                priors[v["id"]] = list(prior)  # a copy, so later updates don't change the reported prior
                post[v["id"]] = list(prior)  # the posterior starts at the prior
        best, best_draw = None, None  # the winning variant for this request
        for v in variants:  # list order fixes the draw sequence and the tie-break
            if v["launch_at"] <= i:  # only live variants get a draw
                a, b = post[v["id"]]  # its current belief
                draw = sample_beta(a, b)  # one plausible success rate; the only randomness
                if best is None or draw > best_draw:  # strictly greater, so ties keep the earlier variant
                    best, best_draw = v["id"], draw  # new leader for this request
        r = req["outcomes"][best]  # observe only what the served prompt did
        post[best][0] += r  # a success adds to a
        post[best][1] += 1 - r  # a failure adds to b
        alloc[best] += 1  # traffic accounting
        reward += r  # total completions
        choices.append(best)  # routing log

    leader = None  # the best variant that earned its evidence
    for v in variants:  # list order, so earlier variants win ties
        if alloc[v["id"]] == 0:  # never served: all its confidence is borrowed
            continue  # can't lead
        a, b = post[v["id"]]  # this variant's posterior
        # a / (a + b) > leader's mean, cross-multiplied so integer ties are exact
        if leader is None or a * (post[leader][0] + post[leader][1]) > post[leader][0] * (a + b):
            leader = v["id"]  # strictly better mean
    # everything the driver compares
    return {"choices": choices, "allocations": alloc, "priors": priors, "posteriors": post, "reward": reward, "leader": leader}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | choices concise, friendly, concise; 6 draws | the basic loop; exact tie goes to the earlier variant |
| Example 2 | `v1-short` prior `(8, 4)`; leader `v1` | warm start at launch; a never-served variant can't lead |
| Example 3 | 2 draws, posterior `(2, 2)` | one draw per request even with one variant |
| three arms from cold | checklist gets 81 of 100, leader checklist, reward 53 | exploration finds the best arm |
| warm launch and cold launch | `v1-tone` prior `(10, 12)`, 230 draws, leader `v1-tone` | two launches mid-flight, warm and cold |
| warm-start chain | priors `b (7, 3)`, `c (5, 5)`, `d (5, 5)`; `c` never serves | a chain of warm starts from current posteriors |
| leader tie by list order | both `(2, 1)`, leader `x` | strict `>` in the leader comparison |
| zero warm weight | `fork` prior `(1, 1)`, 55 draws | `warm_weight = 0` is a cold start |

## 10. Complexity

Each request makes one draw per active variant, so the run makes at most `R · V` calls to `sample_beta` (300 at the largest test here), plus O(V) bookkeeping per request. The cost that matters is the draw itself: the driver's Beta quantile is a 40-step bisection over a binomial sum. That's why the time limit is generous.

In production a request only needs `V` draws from a Beta distribution, microseconds with NumPy. The harder part is that rewards are delayed: onboarding finishes hours after routing. Real systems log each choice and update the posteriors in batches from a reward log, which also makes the bandit replayable for audits.

## 11. If you got Wrong Answer

- **The draw log has fewer or more calls than expected, or a Runtime Error says `sample_beta called more times than the scenario allows`.** You're drawing for variants before their launch (the error), or skipping the draw when only one variant is active.
- **Example 1 serves concise three times and the log is empty.** You serve the best posterior mean instead of sampling. No exploration.
- **Example 1's later draws use `(1, 2)` for friendly, which never served.** You updated every arm from the counterfactual outcomes.
- **Example 2's `v1-short` prior is `(1, 1)`.** You ignored `warm_start_from`.
- **Example 2's `v1-short` prior is `(3, 1)`, or "zero warm weight" shows `fork` at `(6, 1)`.** You copied the parent's posterior instead of using the `warm_weight` budget.
- **Example 2's leader is `v1-short`.** A variant with zero allocations can't lead.
- **"leader tie by list order" picks `y`.** Use strict `>` when comparing means.

## 12. Follow-ups an interviewer might ask

- *Thompson sampling or a fixed A/B test?* Bandits minimize regret, but they don't give you a clean effect estimate, because allocation depends on the data. If you need to report "the checklist prompt lifts completion by 4 points", run a fixed split (problem 146, ab-test-significance) or reweight by the logged serve probabilities.
- *What about epsilon-greedy?* It explores at a fixed rate forever, even after the winner is obvious. Thompson's exploration shrinks as posteriors tighten. Epsilon-greedy is simpler to reason about and to cap.
- *The world changes: the best prompt in March is not the best in May.* Add forgetting: decay `a` and `b` toward the prior over time, or use a sliding window, so old evidence doesn't freeze the posterior.
- *A variant starts producing unsafe answers.* That's a guardrail outside the bandit. Remove the variant from the active set with a kill switch, no matter what its conversion posterior says.
- *How would you choose `warm_weight`?* Treat it as "how many conversations is the parent's evidence worth for this child". A small tone change might justify 20 to 50; a rewritten prompt deserves a cold start.
