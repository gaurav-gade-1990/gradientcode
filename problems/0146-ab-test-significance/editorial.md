## Approach

Four numbers drive the readout: is the allocation healthy (SRM), is the difference real (z-test), how big could it be (CI), and have we collected what we promised (sample size).

**Normal quantiles without SciPy.** `math.erf` gives $\Phi$. It is monotone, so bisection on `[-10, 10]` converges to machine precision well inside 100 steps:

```python
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

**Pooled test, unpooled interval.** Under $H_0$ both arms share one rate, so the test statistic uses $\hat p$. The interval describes the difference you actually observed, so it uses each arm's own variance. The p-value uses `erfc` because `2 * (1 - Phi(z))` rounds to 0 once $z > 8$.

**Sample size.** The standard two-proportion formula, with $z_{1-\alpha/2}$ for the two-sided test and $z_{\text{power}}$ for the alternative. For a 10% baseline and a 1-point MDE it asks for about 14,750 users per arm.

**SRM.** A 1-df chi-square survival function is $\operatorname{erfc}(\sqrt{\chi^2/2})$. Then the rule table runs top to bottom.

## Common mistakes

- **A one-sided p-value**, `1 - Phi(|z|)`, reported for a two-sided test. Half the p-value means twice the false ships.
- **Unpooled SE in the test.** It's close to the pooled one for large balanced arms, but it isn't the test you pre-registered, and it drifts for small or skewed arms.
- **Skipping the SRM check.** A bot filter or a redirect bug that drops users from one arm biases the treatment effect in ways no p-value can see. Check SRM first, always.
- **Shipping on a peek.** Checking a fixed-horizon test every day and stopping at the first p < 0.05 inflates the false-positive rate several times over. Harm is the exception: stopping a test to protect users is fine.
- **`z_(1 - alpha)` instead of `z_(1 - alpha/2)`.** That gives a CI that's too narrow and a sample size that's too small.

## Production notes

- Experiment platforms (Optimizely, Statsig, Eppo, and in-house systems at Microsoft and Booking) run an SRM check on every readout and block the scorecard when it fires. Kohavi's *Trustworthy Online Controlled Experiments* reports that SRM shows up in about 6% of experiments.
- If you really want to peek daily, use a sequential method (mSPRT, always-valid p-values, or alpha spending) instead of this fixed-horizon test. Statsig and Optimizely both ship one.
- Add **guardrail metrics** (latency, refund rate, LLM cost per session) with their own rollback rule, and CUPED variance reduction to reach the planned power sooner.
- Pairs with `canary-analysis` (the same "promote, rollback or extend" shape over time windows) and with `thompson-prompt-variants` when you'd rather minimize regret than estimate an effect.
