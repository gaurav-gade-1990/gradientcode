import numpy as np


def cases():
    rng = np.random.default_rng(67)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]]), "positions": np.array([0, 1, 2])},
         "explanation": "d = 2, so there is one pair with theta = 1. The vector (1, 0) rotates by 0, 1 and 2 radians: (cos p, sin p)."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[1.0, 2.0, 3.0, 4.0]]), "positions": np.array([1])},
         "explanation": "Pairs are (x0, x2) = (1, 3) at theta 1 and (x1, x3) = (2, 4) at theta 1/100."},
        {"name": "position zero is identity", "args": {"x": rng.normal(size=(3, 8)), "positions": np.zeros(3, dtype=int)}},
        {"name": "offset positions", "args": {"x": rng.normal(size=(4, 8)), "positions": np.array([10, 11, 12, 13])}},
        {"name": "batched heads", "args": {"x": rng.normal(size=(2, 3, 5, 16)), "positions": np.arange(5)}},
        {"name": "non-contiguous positions", "args": {"x": rng.normal(size=(2, 4, 6)), "positions": np.array([0, 7, 3, 100])}},
        {"name": "large positions", "args": {"x": rng.normal(size=(3, 32)), "positions": np.array([1000, 50000, 100000])}},
        {"name": "custom base", "args": {"x": rng.normal(size=(6, 4)), "positions": np.arange(6), "base": 500000.0}},
    ]
