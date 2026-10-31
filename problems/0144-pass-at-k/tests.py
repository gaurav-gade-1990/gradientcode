import numpy as np


def _outcomes(rng, n, rate):
    return [int(x) for x in (rng.random(n) < rate)]


def cases():
    rng = np.random.default_rng(144)
    big = {"humaneval/%03d" % i: _outcomes(rng, 2000, r) for i, r in enumerate([0.002, 0.03, 0.4, 0.0, 0.9])}
    mixed = {"mbpp/%d" % i: _outcomes(rng, n, r) for i, (n, r) in enumerate([(200, 0.05), (200, 0.6), (40, 0.1), (5, 0.4), (200, 0.0), (8, 1.0)])}
    lopsided = {"repo/fix-imports": [1] * 180 + [0] * 20, "repo/race-condition": [0] * 9 + [1], "repo/sql-migration": [0] * 10}
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"samples": {"two-sum": [1, 0, 0, 1, 0], "lru-cache": [0, 0, 0, 0, 0]}, "ks": [1, 2], "gate": {"k": 1, "min_score": 0.15}},
         "explanation": "two-sum has n=5, c=2. pass@1 = 1 - 3/5 = 0.4 and pass@2 = 1 - C(3,2)/C(5,2) = 1 - 3/10 = 0.7. lru-cache never passes, so both are 0. The pass@1 score is (0.4 + 0) / 2 = 0.2 >= 0.15, so it ships."},
        {"name": "Example 2", "hidden": False,
         "args": {"samples": {"parse-csv": [1, 1, 0, 1], "rate-limiter": [0, 1, 0]}, "ks": [1, 4], "gate": {"k": 4, "min_score": 0.9}},
         "explanation": "rate-limiter has only 3 samples, so pass@4 is None and it is skipped. parse-csv has n-c = 1 < 4, so pass@4 = 1.0. The pass@4 score is 1.0 over the one remaining problem."},
        {"name": "Example 3", "hidden": False,
         "args": {"samples": {"merge-intervals": [0, 1, 0, 0]}, "ks": [8], "gate": {"k": 8, "min_score": 0.5}},
         "explanation": "Every problem is skipped for k=8, so the score is None and the gate does not ship."},
        {"name": "large n, k sweep", "args": {"samples": big, "ks": [1, 10, 100, 1000], "gate": {"k": 10, "min_score": 0.4}}},
        {"name": "mixed sample counts", "args": {"samples": mixed, "ks": [1, 5, 10, 50], "gate": {"k": 10, "min_score": 0.45}}},
        {"name": "macro vs pooled", "args": {"samples": lopsided, "ks": [1, 5], "gate": {"k": 1, "min_score": 0.6}}},
        {"name": "k equals n", "args": {"samples": {"a": [0, 0, 1], "b": [0, 0, 0], "c": [1, 1, 1]}, "ks": [3, 1, 2], "gate": {"k": 3, "min_score": 0.66}}},
        {"name": "single sample per problem", "args": {"samples": {"p%d" % i: [1] if i % 3 == 0 else [0] for i in range(9)}, "ks": [1, 2], "gate": {"k": 1, "min_score": 0.34}}},
        {"name": "all pass", "args": {"samples": {"x": [1] * 50, "y": [1] * 7}, "ks": [10], "gate": {"k": 10, "min_score": 1.0}}},
    ]
