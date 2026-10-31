import numpy as np


def cases():
    rng = np.random.default_rng(4)
    same = rng.normal(size=(20, 8))
    dup = rng.normal(size=(6, 5)) * 3
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"A": np.array([[0.0, 0.0], [3.0, 4.0]]), "B": np.array([[0.0, 0.0], [6.0, 8.0], [3.0, 0.0]])},
         "explanation": "Row [3, 4] is 5 from the origin, 5 from [6, 8] and 4 from [3, 0]."},
        {"name": "Example 2", "hidden": False,
         "args": {"A": np.array([[1.0, 2.0, 2.0]]), "B": np.array([[1.0, 2.0, 2.0], [0.0, 0.0, 0.0]])},
         "explanation": "A point is 0 from itself. ||[1, 2, 2]|| = 3."},
        {"name": "A equals B (rounding goes negative)", "args": {"A": same, "B": same.copy()}},
        {"name": "duplicate rows", "args": {"A": np.vstack([dup, dup[:2]]), "B": np.vstack([dup[3:], dup])}},
        {"name": "random rectangular", "args": {"A": rng.normal(size=(9, 4)), "B": rng.normal(size=(13, 4))}},
        {"name": "one dimension", "args": {"A": np.array([[1.0], [-2.0], [5.0]]), "B": np.array([[0.0], [5.0]])}},
        {"name": "single pair", "args": {"A": np.array([[1.0, 1.0, 1.0, 1.0]]), "B": np.array([[-1.0, -1.0, -1.0, -1.0]])}},
        {"name": "wide features", "args": {"A": rng.uniform(-10, 10, size=(12, 64)), "B": rng.uniform(-10, 10, size=(10, 64))}},
        {"name": "large (1000 x 1000, timed)", "args": {"seed": 4004, "n": 1000, "m": 1000, "d": 32}},
    ]
