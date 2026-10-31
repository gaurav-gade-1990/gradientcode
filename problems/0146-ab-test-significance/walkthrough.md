## 1. What the problem is really asking

An experiment service calls your function at every daily readout, and a PM acts on the `decision` it returns. So the job isn't just "compute a p-value". It's "compute four health and evidence numbers, then apply a fixed rule table in order, so the PM never acts on a broken or premature result."

Under the story, this is a **two-proportion z-test wrapped in a decision table**:

| number | question it answers |
|---|---|
| `srm_p_value` | is the traffic split what we planned, or is assignment broken? |
| `z`, `p_value` | is the difference in conversion rates bigger than noise? |
| `ci` | how big could the true difference plausibly be? |
| `required_n_per_arm` | have we collected the sample size the test was designed for? |

Every formula is given in the statement. The work is implementing each one exactly (pooled where it says pooled, two-sided where it says two-sided), building the normal quantile by the prescribed bisection, and checking the rules in order. The judge compares every returned number with `rtol=1e-7`, so the bisection has to be done exactly as written.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `control`, `treatment` | `{"users", "conversions"}` | `n` and `x` for each arm |
| `baseline_rate`, `mde` | pre-registered baseline and the absolute lift to detect | the sample-size formula only, not the test |
| `alpha` | significance level | `p_value < alpha`, and the quantile $1 - \alpha/2$ |
| `power` | target power | the quantile $\Phi^{-1}(\text{power})$ |
| `split` | intended fraction of users in treatment | expected counts for the SRM test |
| `srm_alpha` | SRM alarm level, much stricter than `alpha` | rule 1 |

Three details are easy to miss:

- **The test uses the pooled standard error; the interval uses the unpooled one.** They're different formulas on different lines of the table.
- **`baseline_rate` and `mde` describe the plan, not the data.** The sample size depends only on the plan, so it's `14751` in every case that uses the default plan, whatever the observed rates are.
- **`se` can be 0.** With zero conversions in both arms, the pooled rate is 0 and the standard error is 0. The spec says `z = 0.0`; dividing would crash.

## 3. The math

**The z-test.** Under the null hypothesis both arms share one true rate, so you estimate it from both arms together, $\hat p = (x_c + x_t)/(n_c + n_t)$. The difference of two independent proportions then has variance $\hat p(1-\hat p)(1/n_c + 1/n_t)$, and

$$
z = \frac{p_t - p_c}{\sqrt{\hat p(1-\hat p)\left(\frac{1}{n_c} + \frac{1}{n_t}\right)}}
$$

**The two-sided p-value.** The probability of a $\lvert Z\rvert$ at least this large is $2(1 - \Phi(\lvert z\rvert))$. Since $\Phi(x) = \tfrac12(1 + \operatorname{erf}(x/\sqrt2))$, that's $1 - \operatorname{erf}(\lvert z\rvert/\sqrt2) = \operatorname{erfc}(\lvert z\rvert/\sqrt2)$. Using `erfc` directly avoids computing `1 - (number very close to 1)`, which loses precision.

**The interval.** Here you're describing the difference you observed, not testing a null, so each arm keeps its own variance: $se_u = \sqrt{p_c(1-p_c)/n_c + p_t(1-p_t)/n_t}$, and the interval is $\Delta \pm \Phi^{-1}(1-\alpha/2)\cdot se_u$.

**Sample size.** You need the test statistic to clear $z_a = \Phi^{-1}(1-\alpha/2)$ under the null, and to do so with probability `power` when the true lift is `mde`. Solving both conditions for `n` gives the formula in the statement, with $z_b = \Phi^{-1}(\text{power})$.

**SRM.** With $N$ users and an intended `split`, you expect $E_t = N\cdot\text{split}$ in treatment and $E_c = N(1 - \text{split})$ in control. Pearson's statistic is $\chi^2 = \sum (\text{observed} - \text{expected})^2/\text{expected}$. With one degree of freedom, $\chi^2$ is the square of a standard normal, so $P(\chi^2_1 > c) = P(\lvert Z\rvert > \sqrt c) = \operatorname{erfc}(\sqrt{c/2})$.

## 4. Trace Example 1 by hand

Control `10000 / 1000`, treatment `10000 / 1100`, default plan.

| quantity | computation | value |
|---|---|---|
| $p_c$, $p_t$, $\Delta$ | 1000/10000, 1100/10000 | 0.1, 0.11, 0.01 |
| pooled $\hat p$ | 2100 / 20000 | 0.105 |
| pooled se | $\sqrt{0.105 \cdot 0.895 \cdot 2/10000}$ | 0.004335 |
| `z` | 0.01 / 0.004335 | 2.30663 |
| `p_value` | erfc(2.30663 / √2) | 0.0210752 |
| $z_a$ | bisection for $\Phi^{-1}(0.975)$ | 1.959964 |
| unpooled $se_u$ | $\sqrt{0.09/10000 + 0.0979/10000}$ | 0.0043347 |
| `ci` | 0.01 ± 1.959964 · 0.0043347 | [0.00150406, 0.0184959] |
| $z_b$ | $\Phi^{-1}(0.8)$ | 0.841621 |
| sample size | $(0.849707 + 0.364821)^2 / 0.0001$ = 14750.79, ceiling | 14751 |
| SRM | split is exactly 50/50, $\chi^2 = 0$ | 1 |

Now the rules: SRM is fine, the difference is positive so rule 2 doesn't apply, and `10000 < 14751`, so rule 3 fires: **`keep_running`**. The result is significant, but the test was designed for 14,751 users per arm and this is a peek. Shipping now would be the classic peeking mistake.

**Example 2, the SRM case.** 50,600 control and 49,400 treatment on a 50/50 plan. You expect 50,000 each, so $\chi^2 = 600^2/50000 + 600^2/50000 = 14.4$, and `srm_p_value = erfc(√7.2) = 0.000147802 < 0.001`. Rule 1 fires: **`invalid_srm`**, even though `p_value` is `4.23e-06`. Compare "srm close call is fine": 500 off instead of 600 gives $\chi^2 = 10$ and `0.0015654`, which is above `0.001`, so that test ships.

## 5. Key idea: why the rule order matters

The rules are deliberately asymmetric:

1. **SRM first.** If assignment is broken (a bot filter dropping users from one arm, a redirect that loses some traffic), the two arms aren't comparable, and no p-value can fix that.
2. **Harm before power.** Stopping early to protect users is fine. "significant harm while underpowered" has 6,000 per arm, well short of 14,751, but `p = 0.00026` with $\Delta = -0.02$, so it rolls back.
3. **Power before shipping.** Stopping early to *ship* is not fine. If you check a fixed-horizon test daily and ship at the first `p < 0.05`, the real false-positive rate is several times 5%.
4. **Ship** only when powered and significantly positive.
5. Otherwise, **no_effect**.

## 6. Plan before you code

```
norm_cdf(x) = 0.5 * (1 + erf(x / sqrt 2))
norm_ppf(q) = 100 steps of bisection on [-10, 10]
rates, diff
pooled se -> z (0 if se == 0) -> p_value = erfc(|z| / sqrt 2)
z_a = ppf(1 - alpha/2); unpooled se -> ci
z_b = ppf(power); required = ceil(formula)
expected counts -> chi2 -> srm_p = erfc(sqrt(chi2 / 2))
first matching rule -> decision
```

| # | condition | decision |
|---|---|---|
| 1 | `srm_p < srm_alpha` | `invalid_srm` |
| 2 | `p_value < alpha` and `diff < 0` | `rollback` |
| 3 | either arm below `required` | `keep_running` |
| 4 | `p_value < alpha` and `diff > 0` | `ship` |
| 5 | otherwise | `no_effect` |

## 7. Build it one piece at a time

**Step 1: the normal CDF and quantile.** The bisection must match the spec exactly, including the `< q` test and returning the midpoint:

```python
def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(q):
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if norm_cdf(mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0
```

The interval halves 100 times from width 20, far past double precision, so the result is as exact as `erf` allows.

**Step 2: the test.** Pooled se, with the zero guard:

```python
pooled = (x_c + x_t) / (n_c + n_t)
se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n_c + 1.0 / n_t))
z = diff / se if se > 0 else 0.0
p_value = math.erfc(abs(z) / math.sqrt(2.0))
```

Use the pooled se here, not the unpooled one. For balanced arms they're close (Example 1 gives `z = 2.30694` unpooled versus `2.30663` pooled), but at `rtol=1e-7` that's a wrong answer.

**Step 3: the interval and the sample size.** Both use $z_a = \Phi^{-1}(1 - \alpha/2)$. Halving alpha is what makes it two-sided: with `1 - alpha` you'd get 1.644854 instead of 1.959964, and a sample size of 11620 instead of 14751.

```python
z_a = norm_ppf(1.0 - alpha / 2.0)
se_u = math.sqrt(p_c * (1.0 - p_c) / n_c + p_t * (1.0 - p_t) / n_t)
ci = [diff - z_a * se_u, diff + z_a * se_u]
```

**Step 4: SRM and the decision.** Expected counts come from the total and the plan's `split`, not from 50/50. "srm on uneven plan" has `split = 0.7`: 20,500 users should give 14,350 in treatment, and 13,500 is 850 short, which is a `2.2e-38` p-value.

## 8. Full solution

```python
import math  # erf and erfc give the normal distribution without SciPy


def norm_cdf(x):  # standard normal CDF
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))  # Phi(x) written with the error function


def norm_ppf(q):  # inverse CDF by the bisection the spec prescribes
    lo, hi = -10.0, 10.0  # Phi(-10) is ~0 and Phi(10) is ~1, so the answer is inside
    for _ in range(100):  # each step halves the bracket; 100 steps is far past double precision
        mid = (lo + hi) / 2.0  # try the middle of the bracket
        if norm_cdf(mid) < q:  # the quantile lies to the right of mid
            lo = mid  # move the left edge up
        else:  # the quantile is at or left of mid
            hi = mid  # move the right edge down
    return (lo + hi) / 2.0  # midpoint of the final bracket


def ab_test(control, treatment, plan):  # one daily readout: statistics plus a decision
    n_c, x_c = control["users"], control["conversions"]  # control arm size and successes
    n_t, x_t = treatment["users"], treatment["conversions"]  # treatment arm size and successes
    p_c, p_t = x_c / n_c, x_t / n_t  # observed conversion rates
    diff = p_t - p_c  # the lift we're testing; negative means treatment is worse

    pooled = (x_c + x_t) / (n_c + n_t)  # under the null both arms share one rate
    se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n_c + 1.0 / n_t))  # standard error of diff under the null
    z = diff / se if se > 0 else 0.0  # no conversions anywhere means no evidence either way
    p_value = math.erfc(abs(z) / math.sqrt(2.0))  # two-sided tail, without 1 - Phi cancellation

    alpha = plan["alpha"]  # significance level used by the test and the interval
    z_a = norm_ppf(1.0 - alpha / 2.0)  # two-sided critical value: alpha is split across both tails
    se_u = math.sqrt(p_c * (1.0 - p_c) / n_c + p_t * (1.0 - p_t) / n_t)  # each arm keeps its own variance
    ci = [diff - z_a * se_u, diff + z_a * se_u]  # plausible range for the true lift

    p1 = plan["baseline_rate"]  # the pre-registered control rate
    p2 = p1 + plan["mde"]  # the treatment rate we want to be able to detect
    pbar = (p1 + p2) / 2.0  # average rate for the null-side variance
    z_b = norm_ppf(plan["power"])  # quantile that buys the target power
    # null-side term plus alternative-side term of the two-proportion sample-size formula
    root = z_a * math.sqrt(2.0 * pbar * (1.0 - pbar)) + z_b * math.sqrt(p1 * (1.0 - p1) + p2 * (1.0 - p2))
    required = int(math.ceil(root ** 2 / plan["mde"] ** 2))  # round up: you can't enroll part of a user

    total = n_c + n_t  # everyone assigned so far
    e_t, e_c = total * plan["split"], total * (1.0 - plan["split"])  # what the planned split should give
    chi2 = (n_t - e_t) ** 2 / e_t + (n_c - e_c) ** 2 / e_c  # Pearson statistic for the allocation
    srm_p = math.erfc(math.sqrt(chi2 / 2.0))  # 1-df chi-square tail, via the normal

    if srm_p < plan["srm_alpha"]:  # the split itself is broken
        decision = "invalid_srm"  # nothing else can be trusted
    elif p_value < alpha and diff < 0:  # significant harm
        decision = "rollback"  # protect users even before the test is powered
    elif n_c < required or n_t < required:  # still short of the designed sample size
        decision = "keep_running"  # no shipping on a peek
    elif p_value < alpha and diff > 0:  # powered and significantly better
        decision = "ship"  # promote the treatment
    else:  # powered, and no significant difference
        decision = "no_effect"  # the change doesn't move conversion

    return {  # every number the experiment service displays, plus the action
        "p_control": p_c, "p_treatment": p_t, "diff": diff, "z": z, "p_value": p_value, "ci": ci,
        "required_n_per_arm": required, "srm_p_value": srm_p, "decision": decision,
    }
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | p 0.0210752, required 14751, `keep_running` | rule 3 blocks shipping on a peek |
| Example 2 | SRM p 0.000147802, `invalid_srm` | rule 1 overrides a very significant lift |
| Example 3 | z 3.89816, `ship` | the happy path |
| significant harm while underpowered | diff -0.02, p 0.00026073, `rollback` | rule 2 comes before rule 3 |
| fully powered, no effect | p 0.279129, `no_effect` | rule 5 |
| zero conversions both arms | z 0, p 1, ci [0, 0], required 1141 | the `se > 0` guard |
| 90/10 holdout split | SRM p 1, required 5003, `ship` | expected counts use `split`, not 50/50 |
| srm close call is fine | SRM p 0.0015654, `ship` | strict `<` against a strict `srm_alpha` |
| strict alpha high power | required 91685, `ship` | `alpha` and `power` flow into both quantiles |
| one-sided would ship | p 0.0767057, `no_effect` | two-sided p; one-sided would be 0.0383529 and ship |
| huge z | z 48.4265, p 0 | the tail underflows cleanly to 0 |
| srm on uneven plan | SRM p 2.2057e-38, `invalid_srm` | SRM against a 70/30 plan |

## 10. Complexity

Everything is O(1): a fixed 100-step bisection called twice, and a handful of arithmetic operations. The function runs in microseconds whether an arm has 400 users or 2 million.

The cost that matters in production is statistical, not computational. A 1-point lift on a 10% baseline needs 14,751 users per arm. Halving the MDE roughly quadruples that, because `mde` is squared in the denominator. That's why teams pre-register the MDE, and why variance reduction like CUPED, which shrinks the variance term, is worth real engineering.

## 11. If you got Wrong Answer

- **Every case is off, with `required_n_per_arm` at 11620 instead of 14751.** You used $\Phi^{-1}(1 - \alpha)$. Two-sided needs $1 - \alpha/2$.
- **Every nonzero p-value is half the expected value, and "one-sided would ship" ships.** You used `1 - norm_cdf(abs(z))`. That's one tail.
- **`z` is 2.30694 in Example 1 instead of 2.30663.** You used the unpooled se in the test.
- **Example 2 ships, and "srm on uneven plan" says `keep_running`.** You never check SRM.
- **Example 1 ships, and "zero conversions both arms" says `no_effect`.** You're missing the sample-size rule.
- **"zero conversions both arms" crashes with `ZeroDivisionError`.** Guard `se > 0`. (`se_u` is 0 too, but it's only multiplied, so the interval is just `[0, 0]`.)
- **The quantiles differ in the last digits.** Follow the bisection exactly: bracket `[-10, 10]`, 100 steps, `< q` moves `lo`, return the midpoint.

## 12. Follow-ups an interviewer might ask

- *The PM wants to look every day. What do you change?* Use a sequential method instead of this fixed-horizon test: mSPRT, always-valid p-values, or an alpha-spending plan. Statsig and Optimizely both ship one. Problem 147 (canary-analysis) uses the same promote, roll back or extend shape over time windows.
- *How common is SRM, and what causes it?* Kohavi's *Trustworthy Online Controlled Experiments* reports it in about 6% of experiments. Typical causes are bot filtering applied to one arm, redirects that lose users, and caching that serves one variant before assignment.
- *Conversion went up but latency did too. Ship?* Add guardrail metrics (latency, refund rate, LLM cost per session), each with its own rollback rule, and require them to pass alongside the primary metric.
- *You'd rather spend less traffic on the losing variant.* Use a bandit, like problem 152 (thompson-prompt-variants). You trade a clean effect estimate for lower regret.
- *Why is `srm_alpha` so much smaller than `alpha`?* SRM is checked on every readout of every experiment, so a loose threshold would raise false alarms constantly. And when it fires it blocks the whole result, so you want it to fire only on real breakage.
