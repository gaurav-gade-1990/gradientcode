def _beta_cdf(x, a, b):
    """Regularized incomplete beta I_x(a, b) for integer a, b >= 1: P(Binomial(a + b - 1, x) >= a).
    Only +, *, / are used, so the result is bit-identical on every platform."""
    n = a + b - 1
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    q = 1.0 - x
    term = 1.0
    for _ in range(n):
        term *= q                     # P(j = 0) = q^n
    ratio = x / q
    total = 0.0
    for j in range(n + 1):
        if j >= a:
            total += term
        term = term * (n - j) / (j + 1) * ratio
    return total


def _beta_quantile(u, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if _beta_cdf(mid, a, b) < u:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def run(ns, variants, requests, warm_weight, uniforms):
    """sample_beta(a, b) maps the next uniform through the Beta(a, b) quantile and records (a, b)."""
    draws = list(uniforms)
    calls = []

    def sample_beta(a, b):
        if int(a) != a or int(b) != b or a < 1 or b < 1:
            raise ValueError("sample_beta expects integer a, b >= 1, got (%r, %r)" % (a, b))
        if not draws:
            raise AssertionError("sample_beta called more times than the scenario allows")
        calls.append([int(a), int(b)])
        return _beta_quantile(draws.pop(0), int(a), int(b))

    out = ns["run_thompson"](variants, requests, sample_beta, warm_weight)
    return {"report": out, "beta_calls": calls}
