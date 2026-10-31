SYSTEM = "You are a strict evaluator. Compare two responses to the same customer question."
TEMPLATE = (
    "Question: {question}\n\n"
    "[Response 1]\n{first}\n\n"
    "[Response 2]\n{second}\n\n"
    "Which response is better? Reply with exactly one of: 1, 2, tie."
)
LABELS = ("candidate", "baseline", "tie")
WINNER = {
    "ab": {"1": "candidate", "2": "baseline"},
    "ba": {"1": "baseline", "2": "candidate"},
}


def _ask(judge, question, first, second):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": TEMPLATE.format(question=question, first=first, second=second)},
    ]
    token = (judge.complete(messages).content or "").strip().lower().rstrip(".")
    return token if token in ("1", "2", "tie") else "invalid"


def _kappa(judged, labels):
    m = len(labels)
    if m == 0:
        return None
    p_o = sum(1 for a, b in zip(judged, labels) if a == b) / m
    p_e = sum((judged.count(l) / m) * (labels.count(l) / m) for l in LABELS)
    if p_e == 1:
        return 1.0
    return (p_o - p_e) / (1 - p_e)


def evaluate_with_judge(judge, pairs, human, policy):
    verdicts = {}
    parse_errors = biased = inconsistent = 0
    for p in pairs:
        ab = _ask(judge, p["question"], p["candidate"], p["baseline"])
        ba = _ask(judge, p["question"], p["baseline"], p["candidate"])
        parse_errors += (ab == "invalid") + (ba == "invalid")
        w_ab, w_ba = WINNER["ab"].get(ab, "tie"), WINNER["ba"].get(ba, "tie")
        consistent = w_ab == w_ba
        inconsistent += not consistent
        biased += ab == ba and ab in ("1", "2")
        verdicts[p["pair_id"]] = {"ab": ab, "ba": ba, "final": w_ab if consistent else "tie", "consistent": consistent}

    n = len(pairs)
    finals = [verdicts[p["pair_id"]]["final"] for p in pairs]
    wins, losses, ties = finals.count("candidate"), finals.count("baseline"), finals.count("tie")
    labeled = [p["pair_id"] for p in pairs if p["pair_id"] in human]
    kappa = _kappa([verdicts[i]["final"] for i in labeled], [human[i] for i in labeled])
    score = (wins + 0.5 * ties) / n
    bias_rate = biased / n

    if kappa is not None and kappa < policy["min_kappa"]:
        decision = "judge_unreliable"
    elif bias_rate > policy["max_position_bias"]:
        decision = "judge_unreliable"
    elif score >= policy["ship_score"]:
        decision = "ship"
    else:
        decision = "hold"

    return {
        "verdicts": verdicts,
        "win_rate": wins / n, "loss_rate": losses / n, "tie_rate": ties / n, "score": score,
        "inconsistency_rate": inconsistent / n, "position_bias_rate": bias_rate,
        "parse_errors": parse_errors, "kappa": kappa, "decision": decision,
    }
