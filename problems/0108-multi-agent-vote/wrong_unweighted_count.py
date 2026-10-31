def normalize(answer):
    if answer is None:
        return None
    s = " ".join(answer.strip().lower().split()).rstrip(".!?")
    return s or None


def aggregate(votes, quorum):
    # Bug: plain headcount; the confidence is ignored, so three unsure agents outvote one sure one.
    scores, counts, first = {}, {}, {}
    for i, v in enumerate(votes):
        a = normalize(v["answer"])
        if a is None:
            continue
        c = min(1.0, max(0.0, float(v["confidence"])))
        if a not in scores:
            scores[a], counts[a], first[a] = 0.0, 0, i
        scores[a] += 1.0
        counts[a] += 1
    scores = {a: round(s, 9) for a, s in scores.items()}
    voters = sum(counts.values())
    out = {"decision": None, "reason": "no_quorum", "scores": scores, "voters": voters}
    if voters < quorum:
        return out
    best = max(scores.values())
    top = [a for a in scores if scores[a] == best]
    out["decision"] = min(top, key=lambda a: (-counts[a], first[a]))
    out["reason"] = "highest_score" if len(top) == 1 else "tie_break"
    return out
