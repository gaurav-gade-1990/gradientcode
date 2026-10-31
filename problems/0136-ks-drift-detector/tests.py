import numpy as np


def _ints(a):
    return [int(x) for x in a]


def _f(a, d=1):
    return [round(float(x), d) for x in a]


def _with_nulls(rng, values, rate):
    return [None if rng.random() < rate else v for v in values]


def cases():
    rng = np.random.default_rng(136)
    ref = {
        "prompt_tokens": _ints(np.round(rng.lognormal(np.log(180), 0.5, 400))),
        "latency_ms": _f(rng.gamma(4.0, 90.0, 400)),
        "account_age_days": _with_nulls(rng, _ints(rng.integers(1, 1500, 400)), 0.05),
        "retrieved_chunks": _ints(rng.choice(range(9), 400, p=[.02, .05, .1, .18, .25, .2, .1, .06, .04])),
        "sentiment_score": _f(np.clip(rng.normal(0.1, 0.35, 400), -1, 1), 2),
        "attachments_count": _ints(rng.poisson(0.4, 400)),
    }
    quiet = {
        "prompt_tokens": _ints(np.round(rng.lognormal(np.log(180), 0.5, 250))),
        "latency_ms": _f(rng.gamma(4.0, 90.0, 250)),
        "account_age_days": _with_nulls(rng, _ints(rng.integers(1, 1500, 250)), 0.05),
        "retrieved_chunks": _ints(rng.choice(range(9), 250, p=[.02, .05, .1, .18, .25, .2, .1, .06, .04])),
        "sentiment_score": _f(np.clip(rng.normal(0.1, 0.35, 250), -1, 1), 2),
        "attachments_count": _ints(rng.poisson(0.4, 250)),
    }
    incident = {
        "prompt_tokens": _ints(np.round(rng.lognormal(np.log(260), 0.55, 250))),
        "latency_ms": _f(rng.gamma(4.0, 90.0, 250) * 1.12),
        "account_age_days": _with_nulls(rng, _ints(rng.integers(1, 1500, 250)), 0.4),
        "retrieved_chunks": _ints(rng.choice(range(9), 250, p=[.02, .05, .1, .18, .25, .2, .1, .06, .04])),
        "sentiment_score": _f(np.clip(rng.normal(-0.05, 0.4, 250), -1, 1), 2),
    }
    crm_outage = dict(quiet)
    crm_outage["account_age_days"] = [None] * 120 + [v for v in quiet["account_age_days"][:130]]
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"reference": {"latency_ms": [120, 135, 150, 160, 180, 210, 240, 300],
                                "prompt_tokens": [90, 110, 140, 150, 175, 190, 220, 260]},
                  "current": {"latency_ms": [150, 190, 230, 260, 310, 340, 390, 450],
                              "prompt_tokens": [95, 105, 150, 160, 170, 200, 210, 250]},
                  "alpha": 0.05, "min_samples": 5},
         "explanation": "latency_ms: at x = 180 the reference CDF is 5/8 and the current CDF is 1/8, so D = 0.5. x = 210 and 240 reach the same gap, and at reports the smallest. With n_e = 4, lambda = (2 + 0.12 + 0.055) * 0.5 = 1.0875 and p = 0.188. Two features were tested, so the threshold is 0.05 / 2 = 0.025 and neither drifts."},
        {"name": "Example 2", "hidden": False,
         "args": {"reference": {"latency_ms": [210, 220, 230, 240, 250, 260, 270, 280, 290, 300],
                                "account_age_days": [400, None, 35, 900, None, 12],
                                "attachments_count": [0, 1, 0, 0, 2, 0, 0, 1, 0, 0]},
                  "current": {"latency_ms": [610, 640, 655, 700, 720, 760, 790, 810, 850, 900],
                              "account_age_days": [None, None, None, 20, 300, None]},
                  "alpha": 0.05, "min_samples": 3},
         "explanation": "attachments_count is absent from current: status missing. account_age_days keeps 4 and 2 non-null values, below min_samples = 3: insufficient_data. Only latency_ms is tested, so the threshold stays 0.05. Every current value is above every reference value, D = 1 at x = 300, and p is about 1.9e-5: drifted."},
        {"name": "quiet hour, six features", "args": {"reference": ref, "current": quiet}},
        {"name": "prompt-length incident", "args": {"reference": ref, "current": incident}},
        {"name": "incident at alpha 0.01", "args": {"reference": ref, "current": incident, "alpha": 0.01}},
        {"name": "CRM outage nulls", "args": {"reference": ref, "current": crm_outage}},
        {"name": "high min_samples skips sparse", "args": {"reference": ref, "current": incident, "min_samples": 300}},
        {"name": "nothing tested", "args": {"reference": {"latency_ms": [100.0] * 5}, "current": {"tokens": [3] * 50}}},
        {"name": "shift between reference points",
         "args": {"reference": {"latency_ms": [100 + 10 * i for i in range(40)]},
                  "current": {"latency_ms": [105 + 10 * i for i in range(20)] + [104.5] * 20}}},
        {"name": "tied integer feature", "args": {"reference": {"retrieved_chunks": ref["retrieved_chunks"]},
                                                  "current": {"retrieved_chunks": _ints(rng.choice(range(9), 300, p=[.1, .1, .15, .2, .2, .1, .07, .05, .03]))}}},
        {"name": "Bonferroni over tested features only",
         "args": {"reference": {"latency_ms": [200 + 5 * i for i in range(40)], "tool_calls": [1, 2, 1], "gpu_util": [0.7] * 40},
                  "current": {"latency_ms": [265 + 5 * i for i in range(40)], "tool_calls": [3, 4, 2, 5]}}},
        {"name": "identical windows", "args": {"reference": {"sentiment_score": ref["sentiment_score"]}, "current": {"sentiment_score": ref["sentiment_score"]}}},
    ]
