import numpy as np


def cases():
    rng = np.random.default_rng(12)
    X4 = rng.normal(size=(50, 4)) + np.array([3.0, -2.0, 0.0, 5.0])
    y4 = X4 @ np.array([1.0, 0.5, -1.0, 2.0]) + 10.0 + rng.normal(size=50)
    Xd = rng.normal(size=(15, 2))
    Xd = np.hstack([Xd, Xd[:, :1]])
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[1.0], [2.0], [3.0], [4.0]]), "y": np.array([3.0, 5.0, 7.0, 9.0]), "alpha": 5.0},
         "explanation": "Centered, sum(xc^2) = 5 and sum(xc * yc) = 10, so w = 10 / (5 + 5) = 1. Then b = mean(y) - mean(x) * w = 6 - 2.5 = 3.5."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [2.0, 2.0]]), "y": np.array([1.0, 2.0, 3.5, 6.0]), "alpha": 1.0}},
        {"name": "off-center features", "args": {"X": X4, "y": y4, "alpha": 3.0}},
        {"name": "tiny alpha", "args": {"X": X4, "y": y4, "alpha": 1e-6}},
        {"name": "huge alpha", "args": {"X": X4, "y": y4, "alpha": 1e6}},
        {"name": "duplicated column", "args": {"X": Xd, "y": rng.normal(size=15) + 4.0, "alpha": 0.5}},
        {"name": "more features than samples", "args": {"X": rng.normal(size=(4, 7)) + 1.0, "y": rng.normal(size=4) - 3.0, "alpha": 2.0}},
        {"name": "constant feature", "args": {"X": np.hstack([rng.normal(size=(10, 2)), np.full((10, 1), -4.0)]), "y": rng.normal(size=10), "alpha": 0.1}},
    ]
