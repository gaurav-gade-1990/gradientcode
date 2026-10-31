import numpy as np


def cases():
    rng = np.random.default_rng(6)
    corr = rng.normal(size=(200, 3)) @ np.array([[1.0, 0.8, 0.0], [0.0, 0.6, 0.0], [0.0, 0.0, 2.0]]) + np.array([5.0, -3.0, 10.0])
    return [
        {"name": "Example 1", "hidden": False, "args": {"X": np.array([[1.0, 2.0], [3.0, 6.0], [5.0, 10.0]])},
         "explanation": "Column 2 is twice column 1. Var(x1) = 4, Var(x2) = 16, Cov = 8, all divided by n - 1 = 2."},
        {"name": "Example 2", "hidden": False, "args": {"X": np.array([[0.0, 1.0, 5.0], [2.0, 1.0, 1.0]])},
         "explanation": "Two samples. The middle feature is constant, so its row and column are 0."},
        {"name": "nonzero means", "args": {"X": corr}},
        {"name": "two samples", "args": {"X": rng.normal(size=(2, 4))}},
        {"name": "single feature", "args": {"X": rng.normal(size=(10, 1)) * 3 + 7}},
        {"name": "more features than samples", "args": {"X": rng.normal(size=(5, 8))}},
        {"name": "square", "args": {"X": rng.normal(size=(6, 6)) + 2.0}},
        {"name": "larger", "args": {"X": rng.normal(size=(300, 12)) * np.arange(1, 13)}},
        {"name": "huge means, unit spread", "args": {"X": rng.normal(size=(50, 3)) + 1e8}},
    ]
