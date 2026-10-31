PLAN = {"baseline_rate": 0.10, "mde": 0.01, "alpha": 0.05, "power": 0.8, "split": 0.5, "srm_alpha": 0.001}


def _p(**kw):
    p = dict(PLAN)
    p.update(kw)
    return p


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"control": {"users": 10000, "conversions": 1000}, "treatment": {"users": 10000, "conversions": 1100}, "plan": PLAN},
         "explanation": "Day 3 readout. The lift is significant (z = 0.01 / 0.004335 = 2.307, p = 0.021), but detecting a 1-point lift at 80% power needs 14,751 users per arm. Rule 3 says keep running instead of shipping on a peek."},
        {"name": "Example 2", "hidden": False,
         "args": {"control": {"users": 50600, "conversions": 5100}, "treatment": {"users": 49400, "conversions": 5420}, "plan": PLAN},
         "explanation": "A 50/50 split expects 50,000 per arm. chi2 = 600^2/50000 * 2 = 14.4 and the SRM p-value is 0.00015 < 0.001, so the assignment is broken and the decision is invalid_srm, whatever the lift looks like."},
        {"name": "Example 3", "hidden": False,
         "args": {"control": {"users": 20000, "conversions": 2000}, "treatment": {"users": 20000, "conversions": 2240}, "plan": PLAN},
         "explanation": "Both arms are past 14,751 users, the split is exact, and a 1.2-point lift gives p < 0.05, so ship."},
        {"name": "significant harm while underpowered", "args": {"control": {"users": 6000, "conversions": 660}, "treatment": {"users": 6000, "conversions": 540}, "plan": PLAN}},
        {"name": "fully powered, no effect", "args": {"control": {"users": 30000, "conversions": 3000}, "treatment": {"users": 30000, "conversions": 3080}, "plan": PLAN}},
        {"name": "zero conversions both arms", "args": {"control": {"users": 400, "conversions": 0}, "treatment": {"users": 400, "conversions": 0}, "plan": _p(baseline_rate=0.02, mde=0.02)}},
        {"name": "90/10 holdout split", "args": {"control": {"users": 9000, "conversions": 1260}, "treatment": {"users": 81000, "conversions": 12150}, "plan": _p(baseline_rate=0.14, mde=0.02, split=0.9)}},
        {"name": "srm close call is fine", "args": {"control": {"users": 50500, "conversions": 5050}, "treatment": {"users": 49500, "conversions": 5445}, "plan": PLAN}},
        {"name": "strict alpha high power", "args": {"control": {"users": 120000, "conversions": 6000}, "treatment": {"users": 120000, "conversions": 6480}, "plan": _p(baseline_rate=0.05, mde=0.004, alpha=0.01, power=0.9)}},
        {"name": "one-sided would ship", "args": {"control": {"users": 25000, "conversions": 2500}, "treatment": {"users": 25000, "conversions": 2620}, "plan": PLAN}},
        {"name": "huge z", "args": {"control": {"users": 2000000, "conversions": 200000}, "treatment": {"users": 2000000, "conversions": 230000}, "plan": PLAN}},
        {"name": "srm on uneven plan", "args": {"control": {"users": 7000, "conversions": 700}, "treatment": {"users": 13500, "conversions": 1400}, "plan": _p(split=0.7)}},
    ]
