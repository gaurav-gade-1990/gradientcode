import numpy as np


def _tokens(rng, n, median, sigma):
    return [int(x) for x in np.maximum(1, np.round(rng.lognormal(np.log(median), sigma, n)))]


def cases():
    rng = np.random.default_rng(135)
    ref30 = _tokens(rng, 600, 180, 0.5)
    same_day = _tokens(rng, 300, 180, 0.5)
    long_prompts = _tokens(rng, 300, 420, 0.6)
    slight = _tokens(rng, 300, 205, 0.5)
    latency_ref = [round(float(x), 1) for x in rng.gamma(4.0, 90.0, 400)]
    latency_cur = [round(float(x), 1) for x in rng.gamma(4.0, 90.0, 250) + rng.choice([0.0, 2500.0], 250, p=[0.9, 0.1])]
    retries_ref = [int(x) for x in rng.choice([0, 1, 2, 3], 500, p=[0.82, 0.12, 0.04, 0.02])]
    retries_cur = [int(x) for x in rng.choice([0, 1, 2, 3], 300, p=[0.55, 0.25, 0.12, 0.08])]
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"reference": [88, 95, 102, 110, 120, 131, 140, 152, 160, 175, 182, 190, 205, 214, 230, 248, 260, 290, 330, 410],
                  "current": [120, 150, 176, 210, 240, 265, 300, 340, 395, 450],
                  "n_bins": 4},
         "explanation": "prompt_tokens. The reference quartiles are 128.25, 178.5 and 234.5. Today 1, 2, 1 and 6 of the 10 prompts land in the four bins, against 25% each in the reference. Bin 3 contributes (0.6-0.25)*ln(0.6/0.25) = 0.306, the largest term, and PSI = 0.592 is a major shift."},
        {"name": "Example 2", "hidden": False,
         "args": {"reference": [0, 0, 0, 0, 0, 0, 0, 1, 1, 2], "current": [0, 0, 0, 1, 1, 1, 2, 2, 3, 3], "n_bins": 5},
         "explanation": "Retry counts are heavily tied. The quantiles are [0, 0, 0, 1], so after np.unique the edges are [0, 1] and there are only 3 bins: (-inf, 0], (0, 1], (1, inf). The value 1 sits on an edge and stays in bin 1. Shares move from [0.7, 0.2, 0.1] to [0.3, 0.3, 0.4], PSI = 0.795."},
        {"name": "Example 3", "hidden": False,
         "args": {"reference": [120, 135, 150, 160, 170, 185, 200, 220], "current": [125, 140, 152, 158, 172, 185, 205, 215],
                  "n_bins": 4},
         "explanation": "Today's prompts land two per bin, exactly like the reference, so every contribution is 0, PSI = 0 and the feature is stable. All bins tie, so top_bin is the lowest index, 0."},
        {"name": "30-day reference vs a normal day", "args": {"reference": ref30, "current": same_day}},
        {"name": "long-prompt launch", "args": {"reference": ref30, "current": long_prompts}},
        {"name": "slight growth, 20 bins", "args": {"reference": ref30, "current": slight, "n_bins": 20}},
        {"name": "latency tail from a slow replica", "args": {"reference": latency_ref, "current": latency_cur}},
        {"name": "retry storm on tied feature", "args": {"reference": retries_ref, "current": retries_cur, "n_bins": 10}},
        {"name": "today's traffic all in one bin", "args": {"reference": ref30, "current": [999] * 40, "eps": 1e-3}},
        {"name": "edge values exactly on cut points", "args": {"reference": list(range(1, 101)),
                                                              "current": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 10.1, 20.1, 30.1]}},
        {"name": "constant reference", "args": {"reference": [256] * 50, "current": [256] * 30 + [300] * 10, "n_bins": 10}},
        {"name": "single request today", "args": {"reference": ref30[:100], "current": [181], "n_bins": 8}},
    ]
