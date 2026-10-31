import numpy as np

POLICY = {"ship_score": 0.55, "min_kappa": 0.4, "max_position_bias": 0.3}

QUESTIONS = [
    ("Can I change the shipping address after ordering?", "Yes. Open Orders, pick the order, and choose Edit address before it ships.", "Contact support."),
    ("How do I reset 2FA?", "Go to Settings > Security > Reset 2FA and confirm with your backup code.", "Use the Settings page to reset two-factor authentication with a backup code."),
    ("Why was I charged twice?", "One charge is a temporary authorization hold. It drops off within 3 business days.", "You may have ordered twice. Check your orders."),
    ("Do you ship to Canada?", "Yes, to every province. Duties are shown at checkout.", "Yes, we ship to Canada."),
    ("Can I get an invoice with my VAT number?", "Yes. Add your VAT ID under Billing and download the invoice from Orders.", "Invoices are emailed after purchase."),
    ("Is my data used to train models?", "No. Customer data is never used for training. See our DPA.", "We take privacy seriously."),
]


def _pairs(n, rng):
    out = []
    for i in range(n):
        q, a, b = QUESTIONS[i % len(QUESTIONS)]
        out.append({"pair_id": "q%03d" % i, "question": q + ("" if i < len(QUESTIONS) else " (variant %d)" % i), "candidate": a, "baseline": b})
    return out


def _replies(rng, n, p_first_bias, p_cand):
    """A judge that prefers the candidate with prob p_cand but answers '1' regardless with prob p_first_bias."""
    out = []
    for _ in range(n):
        cand_better = rng.random() < p_cand
        for order in ("ab", "ba"):
            if rng.random() < p_first_bias:
                out.append("1")
            elif rng.random() < 0.1:
                out.append("tie")
            else:
                cand_slot = "1" if order == "ab" else "2"
                other = "2" if order == "ab" else "1"
                out.append(cand_slot if cand_better else other)
    return out


def cases():
    rng = np.random.default_rng(145)
    ex = _pairs(3, rng)
    big = _pairs(40, rng)
    big_human = {p["pair_id"]: ("candidate" if i % 3 else "baseline") for i, p in enumerate(big) if i % 4 == 0}
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"pairs": ex, "human": {"q000": "candidate", "q002": "candidate"}, "policy": POLICY, "replies": ["1", "2", "2", "1", "1", "1"]},
         "explanation": "q000: candidate wins in both orders ('1' then '2'). q001: baseline wins in both. q002: '1' both times, the same slot, so the orders disagree. That's a tie and counts as position bias. score = (1 + 0.5) / 3 = 0.5. Kappa on q000 and q002: p_o = 1/2, p_e = (1/2)(2/2) = 1/2, so kappa = 0 < 0.4 and the judge is unreliable."},
        {"name": "Example 2", "hidden": False,
         "args": {"pairs": ex, "human": {}, "policy": POLICY, "replies": ["1.", "2", " TIE ", "tie", "Response 1", "2"]},
         "explanation": "'1.' parses as 1 and ' TIE ' as tie. 'Response 1' is invalid: one parse error, read as a tie, and it disagrees with the candidate win from '2' in the swapped order. Finals are candidate, tie, tie. score = 2/3 >= 0.55 with no human labels, so ship."},
        {"name": "Example 3", "hidden": False,
         "args": {"pairs": ex[:2], "human": {"q000": "candidate", "q001": "baseline"}, "policy": POLICY, "replies": ["1", "2", "2", "1"]},
         "explanation": "Fully consistent and in perfect agreement with the humans: p_o = 1, p_e = 1/2, kappa = 1. The score is 0.5 < 0.55, so hold."},
        {"name": "first-slot biased judge", "args": {"pairs": big, "human": big_human, "policy": POLICY, "replies": _replies(rng, 40, 0.45, 0.6)}},
        {"name": "honest judge ships", "args": {"pairs": big, "human": {}, "policy": POLICY, "replies": _replies(rng, 40, 0.0, 0.75)}},
        {"name": "always prefers candidate text", "args": {"pairs": big[:10], "human": {p["pair_id"]: ("candidate" if i < 8 else "baseline") for i, p in enumerate(big[:10])},
                                                         "policy": dict(POLICY, min_kappa=0.2), "replies": ["1", "2"] * 10}},
        {"name": "all one label agreement", "args": {"pairs": big[:4], "human": {p["pair_id"]: "baseline" for p in big[:4]}, "policy": POLICY, "replies": ["2", "1"] * 4}},
        {"name": "verbose judge replies", "args": {"pairs": big[:5], "human": {}, "policy": dict(POLICY, ship_score=0.0),
                                                   "replies": ["Response 2 is better than response 1", "2", "1", "Tie.", "", "2", "1", "2", "tie", "tie"]}},
        {"name": "inconsistency dilutes wins", "args": {"pairs": big[:8], "human": {}, "policy": dict(POLICY, ship_score=0.6, max_position_bias=1.0),
                                                        "replies": ["1", "2", "1", "2", "1", "2", "1", "1", "2", "2", "1", "1", "2", "2", "tie", "2"]}},
        {"name": "bias exactly at limit", "args": {"pairs": big[:10], "human": {}, "policy": dict(POLICY, max_position_bias=0.3, ship_score=0.3),
                                                   "replies": ["1", "1", "2", "2", "1", "1"] + ["1", "2"] * 7}},
    ]
