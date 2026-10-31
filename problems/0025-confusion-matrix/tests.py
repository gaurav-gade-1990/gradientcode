import numpy as np


def cases():
    rng = np.random.default_rng(25)
    yt = rng.integers(0, 5, size=200)
    noisy = np.where(rng.random(200) < 0.7, yt, rng.integers(0, 5, size=200))
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"y_true": np.array([0, 1, 2, 2, 1]), "y_pred": np.array([0, 2, 2, 2, 1]), "num_classes": 3},
         "explanation": "Sample 1 is a true 1 predicted as 2, so cm[1, 2] = 1. Both true 2s are right, so cm[2, 2] = 2."},
        {"name": "Example 2", "hidden": False,
         "args": {"y_true": np.array([1, 1, 1, 0]), "y_pred": np.array([0, 0, 1, 0]), "num_classes": 2},
         "explanation": "Two true 1s were predicted as 0, so cm[1, 0] = 2. Repeated pairs must be counted every time."},
        {"name": "class never seen", "args": {"y_true": np.array([0, 1, 0]), "y_pred": np.array([1, 1, 0]), "num_classes": 4}},
        {"name": "all correct", "args": {"y_true": np.array([2, 0, 1, 2, 2]), "y_pred": np.array([2, 0, 1, 2, 2]), "num_classes": 3}},
        {"name": "all wrong one way", "args": {"y_true": np.zeros(6, dtype=np.int64), "y_pred": np.full(6, 2), "num_classes": 3}},
        {"name": "empty", "args": {"y_true": np.array([], dtype=np.int64), "y_pred": np.array([], dtype=np.int64), "num_classes": 2}},
        {"name": "single class", "args": {"y_true": np.zeros(4, dtype=np.int64), "y_pred": np.zeros(4, dtype=np.int64), "num_classes": 1}},
        {"name": "noisy classifier", "args": {"y_true": yt, "y_pred": noisy, "num_classes": 5}},
        {"name": "many classes", "args": {"y_true": rng.integers(0, 20, size=500), "y_pred": rng.integers(0, 20, size=500), "num_classes": 20}},
    ]
