# Incident: Bonferroni divided by every column in the schema, including dropped and sparse ones, so real drift on a key feature went unpaged.
import bisect
import math


def ks_statistic(ref, cur):
    """Return (numerator, at): max |a*m - b*n| over the union of values, at its smallest location."""
    n, m = len(ref), len(cur)
    rs, cs = sorted(ref), sorted(cur)
    best, at = -1, None
    for x in sorted(set(rs) | set(cs)):
        a = bisect.bisect_right(rs, x)
        b = bisect.bisect_right(cs, x)
        num = abs(a * m - b * n)
        if num > best:
            best, at = num, x
    return best, at


def kolmogorov_p(D, n, m):
    ne = n * m / (n + m)
    lam = (math.sqrt(ne) + 0.12 + 0.11 / math.sqrt(ne)) * D
    if lam < 0.27:
        return 1.0
    s = 0.0
    for j in range(1, 101):
        s += (-1) ** (j - 1) * math.exp(-2.0 * j * j * lam * lam)
    return min(1.0, max(0.0, 2.0 * s))


def ks_drift(reference, current, alpha=0.05, min_samples=30):
    features, tested = {}, []
    for name in sorted(set(reference) | set(current)):
        ref = [v for v in reference[name] if v is not None] if name in reference else None
        cur = [v for v in current[name] if v is not None] if name in current else None
        row = {"status": None, "n_ref": None if ref is None else len(ref), "n_cur": None if cur is None else len(cur),
               "D": None, "at": None, "p_value": None}
        if ref is None or cur is None:
            row["status"] = "missing"
        elif len(ref) < min_samples or len(cur) < min_samples:
            row["status"] = "insufficient_data"
        else:
            n, m = len(ref), len(cur)
            num, at = ks_statistic(ref, cur)
            row["D"] = num / (n * m)
            row["at"] = at
            row["p_value"] = kolmogorov_p(row["D"], n, m)
            tested.append(name)
        features[name] = row
    threshold = alpha / len(features) if tested else None
    drifted = []
    for name in tested:
        row = features[name]
        if row["p_value"] < threshold:
            row["status"] = "drifted"
            drifted.append(name)
        else:
            row["status"] = "ok"
    drifted.sort(key=lambda k: (features[k]["p_value"], k))
    return {"tested": len(tested), "threshold": threshold, "drifted": drifted, "features": features}
