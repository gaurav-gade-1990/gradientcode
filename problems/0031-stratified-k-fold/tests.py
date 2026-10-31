import numpy as np


def cases():
    rng = np.random.default_rng(31)
    return [
        {"name": "Example 1", "hidden": False, "args": {"y": np.array([0, 1, 0, 1, 0, 1]), "k": 2},
         "explanation": "Class 0 (indices 0, 2, 4) is dealt folds 0, 1, 0. The dealer continues for class 1 (indices 1, 3, 5): folds 1, 0, 1."},
        {"name": "Example 2", "hidden": False, "args": {"y": np.array([5, 2, 2, 5, 2]), "k": 3},
         "explanation": "Class 2 comes first because 2 < 5: indices 1, 2, 4 get folds 0, 1, 2. Class 5 then continues at fold 0: indices 0, 3 get folds 0, 1."},
        {"name": "dealer carries over", "args": {"y": np.array([1, 0, 0, 1, 0, 2, 2, 1]), "k": 3}},
        {"name": "single class", "args": {"y": np.full(7, 4), "k": 3}},
        {"name": "k equals 1", "args": {"y": np.array([3, 1, 2, 1]), "k": 1}},
        {"name": "k equals n", "args": {"y": np.array([1, 0, 1, 0, 2]), "k": 5}},
        {"name": "negative and gapped labels", "args": {"y": np.array([10, -3, 7, -3, 10, 10, 7, -3, 0]), "k": 4}},
        {"name": "minority class", "args": {"y": np.array([0] * 9 + [1] * 2 + [0] * 3), "k": 5}},
        {"name": "random labels", "args": {"y": rng.integers(0, 4, size=40), "k": 5}},
        {"name": "many samples", "args": {"y": rng.choice([-1, 2, 9], size=500, p=[0.6, 0.3, 0.1]), "k": 7}},
    ]
