import numpy as np


def cases():
    rng = np.random.default_rng(22)
    A = rng.normal(size=(5, 5))
    X5 = rng.normal(size=(60, 5)) @ A + np.array([10.0, -5.0, 3.0, 0.0, 7.0])
    X3 = rng.normal(size=(40, 3)) * np.array([3.0, 1.0, 0.3]) - 4.0
    R = np.linalg.qr(rng.normal(size=(3, 3)))[0]
    X3r = X3 @ R
    X8 = rng.normal(size=(100, 8)) @ rng.normal(size=(8, 8))
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0]]), "k": 1},
         "explanation": "All points lie on the line y = x, so the first component is [0.7071, 0.7071] and it explains 100% of the variance."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[2.0, 0.0], [-2.0, 0.0], [0.0, 1.0], [0.0, -1.0], [1.0, 0.5]]), "k": 2},
         "explanation": "The spread is larger along x than along y, so component 1 is close to the x-axis. Each component's largest-magnitude entry is positive."},
        {"name": "correlated 5d top 2", "args": {"X": X5, "k": 2}},
        {"name": "full rank k = d", "args": {"X": X3r, "k": 3}},
        {"name": "single component", "args": {"X": X3r, "k": 1}},
        {"name": "negative pivot", "args": {"X": np.array([[3.0, -6.0, 0.1], [-3.0, 6.0, -0.2], [1.0, -2.0, 0.3], [-1.0, 2.0, 0.0], [0.5, 0.2, -0.1]]), "k": 2}},
        {"name": "off-center 8d", "args": {"X": X8 + 50.0, "k": 4}},
        {"name": "two samples", "args": {"X": np.array([[0.0, 1.0, 2.0], [2.0, 1.0, -2.0]]), "k": 1}},
    ]
