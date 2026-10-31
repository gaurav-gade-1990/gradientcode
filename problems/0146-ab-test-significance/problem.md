Your growth team is testing a new AI-written checkout summary against the current page. The experiment service calls your function at every daily readout, and its `decision` is what the on-call PM acts on.

Implement `ab_test(control, treatment, plan)`.

- `control` and `treatment` are `{"users": int, "conversions": int}`.
- `plan` is `{"baseline_rate", "mde", "alpha", "power", "split", "srm_alpha"}`: the pre-registered baseline conversion rate, the minimum detectable effect (absolute, in rate units), the significance level, the target power, the intended fraction of users assigned to treatment, and the SRM alarm level.

**Normal distribution, no SciPy.** Define

$$
\Phi(x) = \tfrac{1}{2}\left(1 + \operatorname{erf}(x/\sqrt{2})\right)
$$

and the quantile $\Phi^{-1}(q)$ by bisection: start with `lo = -10.0`, `hi = 10.0`, then repeat **100** times: `mid = (lo + hi) / 2`; if `Phi(mid) < q` set `lo = mid`, else `hi = mid`. Return `(lo + hi) / 2`.

**Statistics.** Let $p_c = x_c / n_c$, $p_t = x_t / n_t$, and $\Delta = p_t - p_c$.

| quantity | definition |
|---|---|
| `z` | $\Delta / \sqrt{\hat p(1-\hat p)(1/n_c + 1/n_t)}$ with the pooled rate $\hat p = (x_c + x_t)/(n_c + n_t)$. If the standard error is 0, `z = 0.0`. |
| `p_value` | two-sided: `math.erfc(abs(z) / math.sqrt(2))` |
| `ci` | `[Δ - m·se_u, Δ + m·se_u]` where $m = \Phi^{-1}(1 - \alpha/2)$ and the unpooled $se_u = \sqrt{p_c(1-p_c)/n_c + p_t(1-p_t)/n_t}$ |
| `required_n_per_arm` | with $p_1$ = `baseline_rate`, $p_2 = p_1 + \text{mde}$, $\bar p = (p_1+p_2)/2$, $z_a = \Phi^{-1}(1-\alpha/2)$, $z_b = \Phi^{-1}(\text{power})$: $\left\lceil \left(z_a\sqrt{2\bar p(1-\bar p)} + z_b\sqrt{p_1(1-p_1) + p_2(1-p_2)}\right)^2 / \text{mde}^2 \right\rceil$ as an int |
| `srm_p_value` | a chi-square test (1 degree of freedom) of the allocation: with $N = n_c + n_t$, $E_t = N\cdot\text{split}$, $E_c = N(1-\text{split})$, $\chi^2 = (n_t - E_t)^2/E_t + (n_c - E_c)^2/E_c$, and `srm_p_value = math.erfc(math.sqrt(chi2 / 2))` |

**Decision.** Apply the first rule that matches:

| # | condition | `decision` |
|---|---|---|
| 1 | `srm_p_value < srm_alpha` | `"invalid_srm"`: the assignment is broken, so no result can be trusted |
| 2 | `p_value < alpha` and `Δ < 0` | `"rollback"`: a significant harm, even if the test is not fully powered yet |
| 3 | `n_c < required_n_per_arm` or `n_t < required_n_per_arm` | `"keep_running"`: no early shipping on a peek |
| 4 | `p_value < alpha` and `Δ > 0` | `"ship"` |
| 5 | otherwise | `"no_effect"` |

Return `{"p_control", "p_treatment", "diff", "z", "p_value", "ci", "required_n_per_arm", "srm_p_value", "decision"}`, with `ci` a list of two floats.

**Constraints**

- `1 <= n <= 10**7` per arm and `0 <= conversions <= users`
- `0 < baseline_rate`, `baseline_rate + mde < 1`, `0 < mde`
- `0 < alpha < 1`, `0.5 < power < 1`, `0 < split < 1`, `0 < srm_alpha < 1`
