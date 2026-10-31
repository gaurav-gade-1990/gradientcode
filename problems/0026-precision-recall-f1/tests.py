import numpy as np


def cases():
    rng = np.random.default_rng(26)
    yt = rng.integers(0, 4, size=120)
    yp = np.where(rng.random(120) < 0.6, yt, rng.integers(0, 4, size=120))
    skew_t = np.array([0] * 30 + [1] * 5 + [2] * 2)
    skew_p = np.array([0] * 28 + [1] * 2 + [1] * 3 + [0] * 2 + [2, 0])
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"y_true": np.array([0, 0, 1, 1, 2, 2]), "y_pred": np.array([0, 1, 1, 1, 2, 0]), "num_classes": 3},
         "explanation": "P = (1/2, 2/3, 1), R = (1/2, 1, 1/2), F1 = (1/2, 4/5, 2/3). Each output is the mean over the three classes."},
        {"name": "Example 2", "hidden": False,
         "args": {"y_true": np.array([0, 0, 0, 1]), "y_pred": np.array([0, 0, 0, 0]), "num_classes": 2},
         "explanation": "Class 1 is never predicted, so its precision, recall and F1 are all 0 (zero division gives 0)."},
        {"name": "absent class counts", "args": {"y_true": np.array([0, 1, 1, 0]), "y_pred": np.array([0, 1, 0, 0]), "num_classes": 4}},
        {"name": "perfect", "args": {"y_true": np.array([2, 1, 0, 2]), "y_pred": np.array([2, 1, 0, 2]), "num_classes": 3}},
        {"name": "all wrong", "args": {"y_true": np.array([0, 1, 2]), "y_pred": np.array([1, 2, 0]), "num_classes": 3}},
        {"name": "imbalanced", "args": {"y_true": skew_t, "y_pred": skew_p, "num_classes": 3}},
        {"name": "single class", "args": {"y_true": np.zeros(5, dtype=np.int64), "y_pred": np.zeros(5, dtype=np.int64), "num_classes": 1}},
        {"name": "noisy", "args": {"y_true": yt, "y_pred": yp, "num_classes": 4}},
        {"name": "many classes", "args": {"y_true": rng.integers(0, 15, size=300), "y_pred": rng.integers(0, 12, size=300), "num_classes": 16}},
    ]
