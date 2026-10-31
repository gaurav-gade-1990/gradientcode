import numpy as np


def cases():
    rng = np.random.default_rng(10)
    X_big = rng.normal(size=(150, 6))
    y_big = X_big @ rng.normal(size=6) + 2.5 + 0.1 * rng.normal(size=150)
    X_dup = rng.normal(size=(20, 2))
    X_dup = np.hstack([X_dup, X_dup[:, :1]])
    y_dup = X_dup @ np.array([1.0, -2.0, 1.0]) + 0.5 + 0.05 * rng.normal(size=20)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[1.0], [2.0], [3.0], [4.0]]), "y": np.array([3.0, 5.0, 7.0, 9.0])},
         "explanation": "The points lie exactly on y = 2x + 1, so w = [2] and b = 1."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [2.0, 1.0]]), "y": np.array([1.0, 2.0, 2.5, 4.0])},
         "explanation": "Four points and three unknowns (two weights and a bias), so the fit is not exact."},
        {"name": "single feature noisy", "args": {"X": rng.normal(size=(30, 1)), "y": rng.normal(size=30)}},
        {"name": "many samples", "args": {"X": X_big, "y": y_big}},
        {"name": "duplicated column", "args": {"X": X_dup, "y": y_dup}},
        {"name": "constant feature", "args": {"X": np.hstack([rng.normal(size=(12, 2)), np.full((12, 1), 3.0)]), "y": rng.normal(size=12)}},
        {"name": "underdetermined", "args": {"X": rng.normal(size=(3, 5)), "y": rng.normal(size=3)}},
        {"name": "large intercept", "args": {"X": rng.normal(size=(25, 3)), "y": rng.normal(size=25) + 100.0}},
    ]
