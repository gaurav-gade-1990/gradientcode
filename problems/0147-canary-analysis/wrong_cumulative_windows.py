# Pools every window so far, so a regression that starts in hour two is diluted by an hour of clean traffic.
def p99(latencies):
    if not latencies:
        return None
    xs = sorted(latencies)
    k = (99 * len(xs) + 99) // 100
    return xs[k - 1]


def analyze_canary(windows, policy):
    timeline = []
    pass_streak = fail_streak = 0
    acc = {"baseline": {"requests": 0, "errors": 0, "latencies_ms": []}, "canary": {"requests": 0, "errors": 0, "latencies_ms": []}}
    for w in windows:
        for arm in ("baseline", "canary"):
            acc[arm] = {"requests": acc[arm]["requests"] + w[arm]["requests"], "errors": acc[arm]["errors"] + w[arm]["errors"], "latencies_ms": acc[arm]["latencies_ms"] + w[arm]["latencies_ms"]}
        b, c = acc["baseline"], acc["canary"]
        r_b, e_b, r_c, e_c = b["requests"], b["errors"], c["requests"], c["errors"]
        p_b, p_c = p99(b["latencies_ms"]), p99(c["latencies_ms"])
        row = {
            "window": w["window"],
            "canary_error_rate": e_c / r_c if r_c else None,
            "baseline_error_rate": e_b / r_b if r_b else None,
            "canary_p99": p_c,
            "baseline_p99": p_b,
        }
        if r_c > 0 and 10000 * e_c > policy["abort_error_bp"] * r_c:
            decision, reasons = "rollback", ["abort_error_rate"]
        elif r_c < policy["min_requests"] or r_b < policy["min_requests"]:
            decision, reasons = "extend", ["insufficient_samples"]
        else:
            reasons = []
            if 10000 * (e_c * r_b - e_b * r_c) > policy["max_error_delta_bp"] * r_c * r_b:
                reasons.append("error_rate")
            if p_c is not None and p_b is not None and 100 * p_c > policy["max_p99_pct"] * p_b:
                reasons.append("latency_p99")
            if reasons:
                fail_streak, pass_streak = fail_streak + 1, 0
                decision = "rollback" if fail_streak >= policy["fail_windows"] else "extend"
            else:
                pass_streak, fail_streak = pass_streak + 1, 0
                decision = "promote" if pass_streak >= policy["pass_windows"] else "extend"
                reasons = ["healthy"]
        row["decision"], row["reasons"] = decision, reasons
        timeline.append(row)
        if decision in ("promote", "rollback"):
            return {"decision": decision, "timeline": timeline}
    return {"decision": "inconclusive", "timeline": timeline}
