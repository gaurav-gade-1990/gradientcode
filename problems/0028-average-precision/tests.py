import numpy as np


def cases():
    rng = np.random.default_rng(28)
    y_big = (rng.random(1500) < 0.2).astype(np.int64)
    y_big[0] = 1
    s_big = np.round(y_big * 0.7 + rng.normal(size=1500), 1)
    y_mid = rng.integers(0, 2, size=50)
    y_mid[0] = 1
    return [
        {"name": "Example 1", "hidden": False, "args": {"y_true": np.array([0, 0, 1, 1]), "scores": np.array([0.1, 0.4, 0.35, 0.8])},
         "explanation": "Ranked: 0.8 (pos), 0.4 (neg), 0.35 (pos), 0.1 (neg). Recall reaches 1/2 at precision 1 and 1 at precision 2/3, so AP = 0.5 * 1 + 0.5 * 2/3, about 0.8333."},
        {"name": "Example 2", "hidden": False, "args": {"y_true": np.array([1, 0, 1, 0]), "scores": np.array([0.9, 0.5, 0.5, 0.1])},
         "explanation": "The two 0.5s tie and enter together: one threshold with TP = 2 of 3 predicted. AP = 0.5 * 1 + 0.5 * 2/3."},
        {"name": "perfect ranking", "args": {"y_true": np.array([0, 1, 0, 1, 1]), "scores": np.array([0.1, 0.9, 0.2, 0.8, 0.7])}},
        {"name": "worst ranking", "args": {"y_true": np.array([1, 0, 0, 0]), "scores": np.array([0.0, 0.3, 0.6, 0.9])}},
        {"name": "all positive", "args": {"y_true": np.array([1, 1, 1]), "scores": np.array([0.2, 0.5, 0.2])}},
        {"name": "all scores tied", "args": {"y_true": np.array([0, 1, 0, 0, 1]), "scores": np.full(5, 0.4)}},
        {"name": "tie with a positive first", "args": {"y_true": np.array([1, 0, 0, 1, 0, 1]), "scores": np.array([0.7, 0.7, 0.7, 0.2, 0.9, 0.1])}},
        {"name": "precision dips then rises", "args": {"y_true": np.array([1, 0, 0, 1, 1, 0]), "scores": np.array([6.0, 5.0, 4.0, 3.0, 2.0, 1.0])}},
        {"name": "single sample", "args": {"y_true": np.array([1]), "scores": np.array([0.3])}},
        {"name": "integer scores", "args": {"y_true": y_mid, "scores": rng.integers(0, 5, size=50).astype(float)}},
        {"name": "large imbalanced", "args": {"y_true": y_big, "scores": s_big}},
    ]
