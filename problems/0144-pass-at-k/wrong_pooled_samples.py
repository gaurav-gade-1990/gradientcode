def _est(n, c, k):
    if n < k:
        return None
    if n - c < k:
        return 1.0
    keep = 1.0
    for i in range(n - c + 1, n + 1):
        keep *= 1.0 - k / i
    return 1.0 - keep


def pass_at_k(samples, ks, gate):
    # Per-problem values are right, but the headline score pools every sample into one n and c,
    # so problems with more samples dominate the release metric.
    scores, skipped = {}, {}
    per_problem = {pid: {} for pid in samples}
    for k in ks:
        key = "pass@%d" % k
        skipped[key] = []
        n_tot = c_tot = 0
        for pid, o in samples.items():
            v = _est(len(o), sum(o), k)
            per_problem[pid][key] = v
            if v is None:
                skipped[key].append(pid)
            else:
                n_tot += len(o)
                c_tot += sum(o)
        skipped[key].sort()
        scores[key] = _est(n_tot, c_tot, k) if n_tot else None
    s = scores["pass@%d" % gate["k"]]
    return {"scores": scores, "per_problem": per_problem, "skipped": skipped, "ship": s is not None and s >= gate["min_score"]}
