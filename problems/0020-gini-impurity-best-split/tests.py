import numpy as np


def cases():
    rng = np.random.default_rng(20)
    X4 = rng.normal(size=(60, 4))
    y4 = ((X4[:, 2] > 0.3) ^ (rng.random(60) < 0.1)).astype(int)
    X3 = rng.integers(0, 5, size=(40, 3)).astype(float)
    y3 = rng.integers(0, 3, size=40)
    Xl = np.round(rng.normal(size=(250, 6)), 2)
    yl = (Xl[:, 1] + 0.5 * Xl[:, 4] > 0).astype(int) + (Xl[:, 0] > 1).astype(int)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[1.0], [2.0], [3.0], [4.0]]), "y": np.array([0, 0, 1, 1])},
         "explanation": "The midpoints are 1.5, 2.5 and 3.5. The threshold 2.5 splits the labels into {0, 0} and {1, 1}, both pure, so the score is 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 10.0], [4.0, 30.0]]), "y": np.array([0, 1, 0, 1])},
         "explanation": "On feature 0 the best score is 1/3, at threshold 1.5 (3.5 ties it but comes later). On feature 1 the midpoint 15.0 sends both rows with value 10 left, both labeled 0, so the score is 0."},
        {"name": "noisy single informative feature", "args": {"X": X4, "y": y4}},
        {"name": "integer features with ties", "args": {"X": X3, "y": y3}},
        {"name": "all constant", "args": {"X": np.ones((5, 2)), "y": np.array([0, 1, 1, 0, 1])}},
        {"name": "pure node", "args": {"X": rng.normal(size=(6, 2)), "y": np.zeros(6, dtype=int)}},
        {"name": "tie across features", "args": {"X": np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 1.0], [1.0, 1.0]]), "y": np.array([0, 1, 0, 1])}},
        {"name": "tie within feature", "args": {"X": np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]]), "y": np.array([0, 1, 0, 1, 0, 1])}},
        {"name": "two samples", "args": {"X": np.array([[3.0, -1.0], [1.0, -1.0]]), "y": np.array([2, 5])}},
        {"name": "larger multiclass", "args": {"X": Xl, "y": yl}},
    ]
