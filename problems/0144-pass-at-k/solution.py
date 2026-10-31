def _estimate(n, c, k):
    if n < k:
        return None
    if n - c < k:
        return 1.0
    keep = 1.0
    for i in range(n - c + 1, n + 1):
        keep *= 1.0 - k / i
    return 1.0 - keep


def pass_at_k(samples, ks, gate):
    scores, skipped = {}, {}
    per_problem = {pid: {} for pid in samples}
    for k in ks:
        key = "pass@%d" % k
        vals = []
        skipped[key] = []
        for pid, outcomes in samples.items():
            v = _estimate(len(outcomes), sum(outcomes), k)
            per_problem[pid][key] = v
            if v is None:
                skipped[key].append(pid)
            else:
                vals.append(v)
        skipped[key].sort()
        scores[key] = sum(vals) / len(vals) if vals else None
    score = scores["pass@%d" % gate["k"]]
    return {
        "scores": scores,
        "per_problem": per_problem,
        "skipped": skipped,
        "ship": score is not None and score >= gate["min_score"],
    }
