def normalize(answer):
    if answer is None:
        return None
    s = " ".join(answer.strip().lower().split()).rstrip(".!?")
    return s or None


def aggregate(votes, quorum):
    # Bug: ties are broken alphabetically, which systematically favors labels like "account" over "warranty".
    scores, counts, first = {}, {}, {}
    for i, v in enumerate(votes):
        a = normalize(v["answer"])
        if a is None:
            continue
        c = min(1.0, max(0.0, float(v["confidence"])))
        if a not in scores:
            scores[a], counts[a], first[a] = 0.0, 0, i
        scores[a] += c
        counts[a] += 1
    scores = {a: round(s, 9) for a, s in scores.items()}
    voters = sum(counts.values())
    out = {"decision": None, "reason": "no_quorum", "scores": scores, "voters": voters}
    if voters < quorum:
        return out
    best = max(scores.values())
    top = [a for a in scores if scores[a] == best]
    out["decision"] = min(top, key=lambda a: (-counts[a], a))
    out["reason"] = "highest_score" if len(top) == 1 else "tie_break"
    return out
