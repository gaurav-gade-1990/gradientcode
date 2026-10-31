import numpy as np


def cases():
    rng = np.random.default_rng(29)
    y = rng.integers(0, 2, size=200)
    p = np.clip(0.5 + (y - 0.5) * rng.random(200) * 0.9 + rng.normal(size=200) * 0.1, 0.0, 1.0)
    return [
        {"name": "Example 1", "hidden": False, "args": {"y_true": np.array([1, 0, 1, 0]), "p": np.array([0.9, 0.1, 0.8, 0.3])},
         "explanation": "-(log 0.9 + log 0.9 + log 0.8 + log 0.7) / 4, about 0.1976."},
        {"name": "Example 2", "hidden": False, "args": {"y_true": np.array([1, 0]), "p": np.array([0.0, 0.0]), "eps": 1e-7},
         "explanation": "p = 0 for a positive would be log(0) = -inf. Clipped to 1e-7 the loss is -(log 1e-7 + log(1 - 1e-7)) / 2, about 8.059."},
        {"name": "confident and right", "args": {"y_true": np.array([1, 1, 0, 0]), "p": np.array([1.0, 1.0, 0.0, 0.0])}},
        {"name": "confident and wrong", "args": {"y_true": np.array([0, 1, 1]), "p": np.array([1.0, 0.0, 0.5])}},
        {"name": "large eps", "args": {"y_true": np.array([0, 1, 1, 0, 1]), "p": np.array([0.0, 0.02, 0.97, 1.0, 0.5]), "eps": 0.05}},
        {"name": "all one half", "args": {"y_true": np.array([0, 1, 1, 0, 1, 0]), "p": np.full(6, 0.5)}},
        {"name": "single sample", "args": {"y_true": np.array([1]), "p": np.array([0.25])}},
        {"name": "noisy classifier", "args": {"y_true": y, "p": p}},
    ]
