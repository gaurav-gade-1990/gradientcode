import numpy as np


def cases():
    rng = np.random.default_rng(2)
    return [
        {"name": "Example 1", "hidden": False, "args": {"x": np.array([1.0, 2.0, 3.0])},
         "explanation": "log(e^1 + e^2 + e^3) = 3 + log(e^-2 + e^-1 + 1), about 3.4076."},
        {"name": "Example 2", "hidden": False, "args": {"x": np.array([1000.0, 1000.0])},
         "explanation": "A naive exp(1000) overflows. Shifting by the max gives 1000 + log(2)."},
        {"name": "Example 3", "hidden": False, "args": {"x": np.array([[0.0, 0.0], [1.0, 3.0]]), "axis": 0},
         "explanation": "Reduce down each column: log(e^0 + e^1) and log(e^0 + e^3)."},
        {"name": "large negatives", "args": {"x": np.array([-1000.0, -1001.0, -1002.0])}},
        {"name": "rows far apart", "args": {"x": np.array([[0.0, 1.0, 2.0], [-2000.0, -2001.0, -2000.5]])}},
        {"name": "batch of rows", "args": {"x": rng.normal(size=(8, 10)) * 50}},
        {"name": "3d middle axis", "args": {"x": rng.normal(size=(3, 4, 5)) * 3, "axis": 1}},
        {"name": "negative axis", "args": {"x": rng.normal(size=(4, 6)) * 400, "axis": -2}},
        {"name": "single element", "args": {"x": np.array([-7.5])}},
        {"name": "one dominant term", "args": {"x": np.array([[9000.0, 0.0, -9000.0], [5.0, 5.0, 5.0]])}},
    ]
