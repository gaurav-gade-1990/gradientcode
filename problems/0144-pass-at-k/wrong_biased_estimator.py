def pass_at_k(samples, ks, gate):
    # Plugs the empirical pass rate into 1 - (1 - p)^k: sampling with replacement, biased.
    scores, skipped = {}, {}
    per_problem = {pid: {} for pid in samples}
    for k in ks:
        key = "pass@%d" % k
        vals, skipped[key] = [], []
        for pid, o in samples.items():
            n, c = len(o), sum(o)
            v = None if n < k else 1.0 - (1.0 - c / n) ** k
            per_problem[pid][key] = v
            if v is None:
                skipped[key].append(pid)
            else:
                vals.append(v)
        skipped[key].sort()
        scores[key] = sum(vals) / len(vals) if vals else None
    s = scores["pass@%d" % gate["k"]]
    return {"scores": scores, "per_problem": per_problem, "skipped": skipped, "ship": s is not None and s >= gate["min_score"]}
