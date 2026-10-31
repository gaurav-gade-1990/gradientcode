import math


def pass_at_k(samples, ks, gate):
    # Textbook ratio of binomials in floating point: OverflowError once C(n, k) > 1e308.
    scores, skipped = {}, {}
    per_problem = {pid: {} for pid in samples}
    for k in ks:
        key = "pass@%d" % k
        vals, skipped[key] = [], []
        for pid, o in samples.items():
            n, c = len(o), sum(o)
            if n < k:
                v = None
            elif n - c < k:
                v = 1.0
            else:
                v = 1.0 - float(math.comb(n - c, k)) / float(math.comb(n, k))
            per_problem[pid][key] = v
            if v is None:
                skipped[key].append(pid)
            else:
                vals.append(v)
        skipped[key].sort()
        scores[key] = sum(vals) / len(vals) if vals else None
    s = scores["pass@%d" % gate["k"]]
    return {"scores": scores, "per_problem": per_problem, "skipped": skipped, "ship": s is not None and s >= gate["min_score"]}
