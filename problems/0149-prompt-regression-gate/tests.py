PROMPT = "You are Acme Support. Be concise. Never promise refunds outside the 30-day policy."


def C(i, inp, expect, tags, must=False):
    return {"id": i, "input": inp, "expect": expect, "tags": tags, "must_pass": must}


SMALL = [
    C("refund-window", "Can I return shoes I bought 45 days ago?", ["30-day"], ["refunds"], True),
    C("order-status", "Where is order 1182?", ["tracking"], ["orders"]),
    C("cancel", "Cancel my subscription please", ["cancel"], ["billing"]),
    C("refund-damaged", "My blender arrived broken", ["replacement"], ["refunds"]),
]


def _golden(n_per, tags):
    out = []
    for t in tags:
        for j in range(n_per):
            out.append(C("%s-%02d" % (t, j), "[%s] customer question %d" % (t, j), ["ticket", t], [t, "en" if j % 2 else "es"], j == 0))
    return out


def _resp(golden, fail_ids=(), error_ids=(), shout_ids=()):
    r = {}
    for c in golden:
        if c["id"] in error_ids:
            r[c["input"]] = {"error": "server"}
        elif c["id"] in fail_ids:
            r[c["input"]] = {"content": "Let me look into that for you."}
        else:
            text = "Opened ticket for you. " + " ".join(c["expect"])
            r[c["input"]] = {"content": text.upper() if c["id"] in shout_ids else text}
    return r


def cases():
    small_resp = {
        "Can I return shoes I bought 45 days ago?": {"content": "Sorry, returns are only accepted within our 30-Day window."},
        "Where is order 1182?": {"content": "Order 1182 shipped. Tracking: 1Z999."},
        "Cancel my subscription please": {"content": "Done. I've set your plan to cancel at period end."},
        "My blender arrived broken": {"content": "Sorry about that! I've issued a full refund."},
    }
    big = _golden(5, ["billing", "orders", "refunds", "returns"])
    allpass = {c["id"]: True for c in big}
    ten = _golden(10, ["general"])
    base10 = {c["id"]: j < 8 for j, c in enumerate(ten)}
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"new_prompt": PROMPT, "golden": SMALL, "baseline": {"refund-window": True, "order-status": True, "cancel": False, "refund-damaged": True},
                  "policy": {"max_drop_pp": 30, "min_slice": 3}, "responses": small_resp},
         "explanation": "refund-damaged now promises a refund instead of a replacement, but cancel newly passes, so B = P = 3 and the overall rate is flat. No slice has 3 cases, so none can block. The gate passes. The must-pass refund-window case still matches '30-day' case-insensitively."},
        {"name": "Example 2", "hidden": False,
         "args": {"new_prompt": PROMPT, "golden": SMALL, "baseline": {"refund-window": True, "order-status": True, "cancel": True, "refund-damaged": True},
                  "policy": {"max_drop_pp": 30, "min_slice": 3},
                  "responses": dict(small_resp, **{"Can I return shoes I bought 45 days ago?": {"content": "Sure, I've refunded you."}})},
         "explanation": "The must-pass refund-window case regresses, and 100 * (4 - 2) = 200 > 30 * 4 = 120, so the gate blocks with ['must_pass:refund-window', 'overall']."},
        {"name": "Example 3", "hidden": False,
         "args": {"new_prompt": PROMPT, "golden": SMALL[1:3], "baseline": {"order-status": True, "cancel": True},
                  "policy": {"max_drop_pp": 50, "min_slice": 1}, "responses": {"Where is order 1182?": {"error": "timeout"}, "Cancel my subscription please": small_resp["Cancel my subscription please"]}},
         "explanation": "The model times out on order-status. That counts as a failure, not a crash. Overall, 100 * (2 - 1) = 100 is not greater than 50 * 2 = 100, so the overall rule holds exactly at the limit. The orders slice has 1 case (min_slice is 1) and dropped 100 points > 50, so it blocks."},
        {"name": "exact boundary does not block", "args": {"new_prompt": PROMPT, "golden": ten, "baseline": base10, "policy": {"max_drop_pp": 10, "min_slice": 11},
                                                          "responses": _resp(ten, fail_ids={c["id"] for c in ten[7:]})}},
        {"name": "one slice regresses", "args": {"new_prompt": PROMPT, "golden": big, "baseline": allpass, "policy": {"max_drop_pp": 15, "min_slice": 5},
                                                 "responses": _resp(big, fail_ids={"returns-02", "returns-03"})}},
        {"name": "flaky tiny slice ignored", "args": {"new_prompt": PROMPT, "golden": big + [C("legal-00", "Is this GDPR compliant?", ["dpa"], ["legal"]), C("legal-01", "Where is the DPA?", ["dpa"], ["legal"])],
                                                      "baseline": dict(allpass, **{"legal-00": True, "legal-01": True}), "policy": {"max_drop_pp": 20, "min_slice": 4},
                                                      "responses": _resp(big + [C("legal-00", "Is this GDPR compliant?", ["dpa"], ["legal"]), C("legal-01", "Where is the DPA?", ["dpa"], ["legal"])], fail_ids={"legal-01"})}},
        {"name": "must-pass hidden by gains", "args": {"new_prompt": PROMPT + " Always offer a coupon.", "golden": big,
                                                       "baseline": {c["id"]: c["id"] not in ("orders-03", "orders-04", "billing-04") for c in big},
                                                       "policy": {"max_drop_pp": 10, "min_slice": 5}, "responses": _resp(big, fail_ids={"refunds-00"})}},
        {"name": "provider errors mid-run", "args": {"new_prompt": PROMPT, "golden": big, "baseline": allpass, "policy": {"max_drop_pp": 25, "min_slice": 5},
                                                     "responses": _resp(big, error_ids={"billing-01", "orders-00", "orders-03"})}},
        {"name": "uppercase response", "args": {"new_prompt": PROMPT, "golden": big, "baseline": allpass, "policy": {"max_drop_pp": 0, "min_slice": 5},
                                                "responses": _resp(big, shout_ids={c["id"] for c in big[::3]})}},
        {"name": "missing scripted reply", "args": {"new_prompt": PROMPT, "golden": SMALL, "baseline": {c["id"]: True for c in SMALL}, "policy": {"max_drop_pp": 100, "min_slice": 1},
                                                    "responses": {}}},
    ]
