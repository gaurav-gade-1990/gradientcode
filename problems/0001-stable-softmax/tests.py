import numpy as np


def cases():
    rng = np.random.default_rng(1)
    return [
        {"name": "Example 1", "hidden": False, "args": {"x": np.array([1.0, 2.0, 3.0])},
         "explanation": "exp([1, 2, 3]) / sum(exp([1, 2, 3]))."},
        {"name": "Example 2", "hidden": False, "args": {"x": np.array([1000.0, 1000.0])},
         "explanation": "A naive exp(1000) overflows. Subtracting the max gives exp([0, 0]), so the answer is [0.5, 0.5]."},
        {"name": "Example 3", "hidden": False, "args": {"x": np.array([[1.0, 2.0], [3.0, 5.0]]), "axis": 0}},
        {"name": "large negatives", "args": {"x": np.array([-1000.0, -1001.0, -1002.0])}},
        {"name": "batch of rows", "args": {"x": rng.normal(size=(8, 10)) * 5}},
        {"name": "3d axis 1", "args": {"x": rng.normal(size=(3, 4, 5)), "axis": 1}},
        {"name": "rows with different scales", "args": {"x": np.array([[0.0, 1.0, 2.0], [500.0, 501.0, 502.0]])}},
        {"name": "single element", "args": {"x": np.array([42.0])}},
        {"name": "negative axis", "args": {"x": rng.normal(size=(4, 6)) * 100, "axis": -2}},
    ]
