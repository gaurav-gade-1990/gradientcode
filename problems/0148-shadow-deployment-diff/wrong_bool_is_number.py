# Forgets that bool subclasses int, so an is_refund flag of True agrees numerically with a ticket count of 1.
import json

CLASSES = ("exact", "normalized", "numeric", "mismatch", "shadow_error")


def _norm(s):
    return " ".join(s.lower().strip().rstrip(".!?").split())


def _is_number(x):
    return isinstance(x, (int, float))


def _classify(rec, policy):
    if rec.get("shadow_error") is not None:
        return "shadow_error"
    p, s = rec["primary"], rec["shadow"]
    if json.dumps(p, sort_keys=True) == json.dumps(s, sort_keys=True):
        return "exact"
    if isinstance(p, str) and isinstance(s, str) and _norm(p) == _norm(s):
        return "normalized"
    if _is_number(p) and _is_number(s) and abs(p - s) <= policy["abs_tol"] + policy["rel_tol"] * abs(p):
        return "numeric"
    return "mismatch"


def _summary(classes):
    out = {"total": len(classes)}
    for c in CLASSES:
        out[c] = classes.count(c)
    out["compared"] = out["total"] - out["shadow_error"]
    agree = out["exact"] + out["normalized"] + out["numeric"]
    out["agreement"] = agree / out["compared"] if out["compared"] else None
    return out


def shadow_diff(records, policy):
    per_request = {r["request_id"]: _classify(r, policy) for r in records}
    overall = _summary([per_request[r["request_id"]] for r in records])
    by_seg = {}
    for r in records:
        by_seg.setdefault(r["segment"], []).append(per_request[r["request_id"]])
    segments = {seg: _summary(cls) for seg, cls in by_seg.items()}

    blocking = []
    if overall["agreement"] is None or overall["agreement"] < policy["min_agreement"]:
        blocking.append("overall_agreement")
    if overall["shadow_error"] / overall["total"] > policy["max_error_rate"]:
        blocking.append("shadow_errors")
    for seg in sorted(segments):
        s = segments[seg]
        if s["compared"] >= policy["min_segment"] and s["agreement"] < policy["min_agreement"]:
            blocking.append("segment:%s" % seg)

    return {
        "per_request": per_request,
        "overall": overall,
        "segments": segments,
        "mismatches": [r["request_id"] for r in records if per_request[r["request_id"]] == "mismatch"],
        "blocking": blocking,
        "ready": not blocking,
    }
