# Uses the one-sided quantile z_(1-alpha) for a two-sided CI and power calculation.
import math


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


def ab_test(control, treatment, plan):
    n_c, x_c = control["users"], control["conversions"]
    n_t, x_t = treatment["users"], treatment["conversions"]
    p_c, p_t = x_c / n_c, x_t / n_t
    diff = p_t - p_c

    pooled = (x_c + x_t) / (n_c + n_t)
    se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n_c + 1.0 / n_t))
    z = diff / se if se > 0 else 0.0
    p_value = math.erfc(abs(z) / math.sqrt(2.0))

    alpha = plan["alpha"]
    z_a = norm_ppf(1.0 - alpha)
    se_u = math.sqrt(p_c * (1.0 - p_c) / n_c + p_t * (1.0 - p_t) / n_t)
    ci = [diff - z_a * se_u, diff + z_a * se_u]

    p1 = plan["baseline_rate"]
    p2 = p1 + plan["mde"]
    pbar = (p1 + p2) / 2.0
    z_b = norm_ppf(plan["power"])
    root = z_a * math.sqrt(2.0 * pbar * (1.0 - pbar)) + z_b * math.sqrt(p1 * (1.0 - p1) + p2 * (1.0 - p2))
    required = int(math.ceil(root ** 2 / plan["mde"] ** 2))

    total = n_c + n_t
    e_t, e_c = total * plan["split"], total * (1.0 - plan["split"])
    chi2 = (n_t - e_t) ** 2 / e_t + (n_c - e_c) ** 2 / e_c
    srm_p = math.erfc(math.sqrt(chi2 / 2.0))

    if srm_p < plan["srm_alpha"]:
        decision = "invalid_srm"
    elif p_value < alpha and diff < 0:
        decision = "rollback"
    elif n_c < required or n_t < required:
        decision = "keep_running"
    elif p_value < alpha and diff > 0:
        decision = "ship"
    else:
        decision = "no_effect"

    return {
        "p_control": p_c, "p_treatment": p_t, "diff": diff, "z": z, "p_value": p_value, "ci": ci,
        "required_n_per_arm": required, "srm_p_value": srm_p, "decision": decision,
    }
