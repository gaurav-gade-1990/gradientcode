import numpy as np


def cases():
    rng = np.random.default_rng(27)
    y_big = rng.integers(0, 2, size=2000)
    s_big = np.round(y_big * 0.8 + rng.normal(size=2000), 1)
    y_mid = rng.integers(0, 2, size=60)
    return [
        {"name": "Example 1", "hidden": False, "args": {"y_true": np.array([0, 0, 1, 1]), "scores": np.array([0.1, 0.4, 0.35, 0.8])},
         "explanation": "Of the 4 (positive, negative) pairs, the positives win 3: 0.8 beats both negatives, and 0.35 beats 0.1 but loses to 0.4. AUC = 0.75."},
        {"name": "Example 2", "hidden": False, "args": {"y_true": np.array([1, 0, 1, 0]), "scores": np.array([0.5, 0.5, 0.9, 0.2])},
         "explanation": "The positive at 0.5 ties the negative at 0.5, which counts 1/2. Pairs won: 1 + 0.5 + 1 + 1 = 3.5 of 4, so AUC = 0.875."},
        {"name": "perfect", "args": {"y_true": np.array([0, 1, 0, 1, 1]), "scores": np.array([-2.0, 3.0, -1.0, 2.5, 0.0])}},
        {"name": "inverted", "args": {"y_true": np.array([1, 1, 0, 0]), "scores": np.array([0.1, 0.2, 0.8, 0.9])}},
        {"name": "all scores tied", "args": {"y_true": np.array([1, 0, 0, 1, 0]), "scores": np.full(5, 0.3)}},
        {"name": "tie block across classes", "args": {"y_true": np.array([0, 1, 1, 0, 1, 0, 0]), "scores": np.array([0.2, 0.7, 0.7, 0.7, 0.9, 0.7, 0.1])}},
        {"name": "one positive", "args": {"y_true": np.array([0, 0, 0, 1, 0]), "scores": np.array([3.0, 1.0, 2.0, 2.0, 5.0])}},
        {"name": "integer-valued scores", "args": {"y_true": y_mid, "scores": rng.integers(0, 4, size=60).astype(float)}},
        {"name": "unsorted with negatives", "args": {"y_true": np.array([1, 0, 1, 0, 1, 0]), "scores": np.array([-0.5, -1.5, 2.0, -0.5, 0.0, 2.0])}},
        {"name": "large with ties", "args": {"y_true": y_big, "scores": s_big}},
    ]
