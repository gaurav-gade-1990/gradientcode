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
    # Problems without enough samples are averaged in as 0, silently dragging the score down.
    scores, skipped = {}, {}
    per_problem = {pid: {} for pid in samples}
    for k in ks:
        key = "pass@%d" % k
        vals, skipped[key] = [], []
        for pid, o in samples.items():
            v = _est(len(o), sum(o), k)
            per_problem[pid][key] = v
            if v is None:
                skipped[key].append(pid)
            vals.append(v or 0.0)
        skipped[key].sort()
        scores[key] = sum(vals) / len(vals)
    s = scores["pass@%d" % gate["k"]]
    return {"scores": scores, "per_problem": per_problem, "skipped": skipped, "ship": s is not None and s >= gate["min_score"]}
