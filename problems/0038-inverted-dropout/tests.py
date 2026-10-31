import numpy as np


def cases():
    rng = np.random.default_rng(38)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([1.0, 2.0, 3.0, 4.0]), "keep_prob": 0.5, "u": np.array([0.1, 0.7, 0.4, 0.9])},
         "explanation": "u < 0.5 keeps elements 0 and 2. They are scaled by 1 / 0.5 = 2, giving [2, 0, 6, 0]."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[1.0, -1.0], [2.0, 5.0]]), "keep_prob": 0.8, "u": np.array([[0.3, 0.2], [0.85, 0.5]]), "train": False},
         "explanation": "In eval mode inverted dropout is the identity."},
        {"name": "u equals keep_prob", "args": {"x": np.array([1.0, 1.0, 1.0, 1.0]), "keep_prob": 0.5, "u": np.array([0.5, 0.25, 0.5, 0.75])}},
        {"name": "keep all", "args": {"x": rng.normal(size=(3, 4)), "keep_prob": 1.0, "u": rng.random((3, 4))}},
        {"name": "random 3d", "args": {"x": rng.normal(size=(2, 3, 5)), "keep_prob": 0.7, "u": rng.random((2, 3, 5))}},
        {"name": "low keep", "args": {"x": rng.normal(size=20), "keep_prob": 0.1, "u": rng.random(20)}},
        {"name": "eval random", "args": {"x": rng.normal(size=(4, 4)), "keep_prob": 0.3, "u": rng.random((4, 4)), "train": False}},
    ]
