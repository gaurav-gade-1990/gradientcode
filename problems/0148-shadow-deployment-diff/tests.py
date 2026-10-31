import numpy as np

POLICY = {"abs_tol": 0.01, "rel_tol": 0.001, "min_agreement": 0.9, "max_error_rate": 0.05, "min_segment": 3}


def R(i, seg, p, s, err=None):
    r = {"request_id": i, "segment": seg, "primary": p, "shadow": s}
    if err is not None:
        r["shadow_error"] = err
    return r


def _pol(**kw):
    p = dict(POLICY)
    p.update(kw)
    return p


def _bulk(rng, n):
    intents = ["refund", "cancel", "shipping_status", "billing_question", "bug_report"]
    segs = ["enterprise", "smb", "free"]
    out = []
    for i in range(n):
        seg = segs[int(rng.integers(3))]
        kind = int(rng.integers(4))
        u = rng.random()
        if kind == 0:
            p = intents[int(rng.integers(5))]
            s = p if u < 0.85 else (p.upper() + "." if u < 0.93 else intents[int(rng.integers(5))])
        elif kind == 1:
            p = round(float(rng.uniform(5, 20000)), 2)
            s = p if u < 0.6 else (p + float(rng.normal(0, 0.02 * (1 + p / 1000))) if u < 0.95 else p * 1.5)
        elif kind == 2:
            p = {"intent": intents[int(rng.integers(5))], "priority": int(rng.integers(1, 4))}
            s = dict(p) if u < 0.9 else {"intent": p["intent"], "priority": p["priority"] % 3 + 1}
        else:
            p = bool(u < 0.5)
            s = p if rng.random() < 0.9 else (not p)
        err = "timeout" if (seg == "free" and rng.random() < 0.08) else None
        out.append(R("req-%04d" % i, seg, p, s, err))
    return out


def cases():
    rng = np.random.default_rng(148)
    ex1 = [
        R("req-101", "enterprise", "refund", "refund"),
        R("req-102", "enterprise", "Shipping status", "shipping status."),
        R("req-103", "smb", 129.99, 130.0),
        R("req-104", "smb", "cancel", "billing_question"),
        R("req-105", "smb", {"intent": "refund", "priority": 2}, {"priority": 2, "intent": "refund"}),
    ]
    ex2 = [
        R("req-201", "enterprise", "refund", None, "timeout after 2s"),
        R("req-202", "enterprise", "cancel", "cancel"),
        R("req-203", "free", True, 1),
        R("req-204", "free", 3, 3.0),
    ]
    types = [R("t1", "api", True, 1), R("t2", "api", 1, True), R("t3", "api", 0, False), R("t4", "api", 2, 2.0),
             R("t5", "api", None, 0), R("t6", "api", [1, 2], [1, 2.0]), R("t7", "api", "1", 1)]
    big_money = [R("inv-%d" % i, "billing", v, v + d) for i, (v, d) in enumerate([(12400.0, 0.01), (12400.0, 12.0), (12400.0, 12.5), (80.0, 0.02), (0.5, 0.0101), (99.99, -0.09)])]
    errs = [R("e%d" % i, "free" if i < 6 else "pro", "refund", "refund", "503" if i % 2 == 0 and i < 6 else None) for i in range(12)]
    small_seg = [R("s%d" % i, "enterprise", "cancel", "cancel") for i in range(10)] + [R("x1", "pilot", "refund", "cancel"), R("x2", "pilot", "refund", "refund")]
    strings = [R("n1", "chat", "  Hello   there!  ", "hello there"), R("n2", "chat", "Hello?!", "hello"), R("n3", "chat", "Hi there", "hi  there ..."),
               R("n4", "chat", "Résumé", "résumé"), R("n5", "chat", "ok.", "ok!"), R("n6", "chat", "a. b", "a b"), R("n7", "chat", "", ".")]
    return [
        {"name": "Example 1", "hidden": False, "args": {"records": ex1, "policy": POLICY},
         "explanation": "req-102 differs only in case and the trailing period (normalized). req-103 is within 0.01 + 0.001 * 129.99 (numeric). req-105 has the same canonical JSON (exact). req-104 is a real mismatch. Agreement is 4/5 = 0.8 < 0.9, and smb has 3 compared requests at 2/3, so both block."},
        {"name": "Example 2", "hidden": False, "args": {"records": ex2, "policy": _pol(min_segment=5)},
         "explanation": "req-201 timed out in shadow, so it's excluded from agreement. True vs 1 is a mismatch: a bool is not a number, and the JSON differs. 3 vs 3.0 is numeric, not exact. Agreement is 2/3, and 1/4 = 25% of shadow calls errored."},
        {"name": "type traps", "args": {"records": types, "policy": _pol(min_agreement=0.5)}},
        {"name": "relative tolerance on large totals", "args": {"records": big_money, "policy": _pol(min_segment=10)}},
        {"name": "errors excluded from agreement", "args": {"records": errs, "policy": _pol(max_error_rate=0.3)}},
        {"name": "tiny segment cannot block", "args": {"records": small_seg, "policy": _pol(min_agreement=0.8, min_segment=3)}},
        {"name": "normalization rules", "args": {"records": strings, "policy": _pol(min_segment=100)}},
        {"name": "all shadow errors", "args": {"records": [R("z1", "smb", "a", None, "oom"), R("z2", "smb", "b", None, "oom")], "policy": _pol(max_error_rate=1.0)}},
        {"name": "week of traffic", "args": {"records": _bulk(rng, 600), "policy": _pol(min_agreement=0.85, min_segment=50)}},
    ]
