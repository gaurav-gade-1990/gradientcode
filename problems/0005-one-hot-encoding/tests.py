import numpy as np


def cases():
    rng = np.random.default_rng(5)
    return [
        {"name": "Example 1", "hidden": False, "args": {"labels": np.array([0, 2, 1]), "num_classes": 3},
         "explanation": "Each row has a single 1 in the column of its label."},
        {"name": "Example 2", "hidden": False, "args": {"labels": np.array([1, 1, 0]), "num_classes": 4},
         "explanation": "Classes 2 and 3 never appear, but the output still has 4 columns."},
        {"name": "largest class missing", "args": {"labels": np.array([0, 1, 0, 1]), "num_classes": 5}},
        {"name": "empty", "args": {"labels": np.array([], dtype=np.int64), "num_classes": 3}},
        {"name": "single class", "args": {"labels": np.array([0, 0, 0]), "num_classes": 1}},
        {"name": "one sample", "args": {"labels": np.array([6]), "num_classes": 7}},
        {"name": "random", "args": {"labels": rng.integers(0, 10, size=40), "num_classes": 10}},
        {"name": "many classes", "args": {"labels": rng.integers(0, 50, size=25), "num_classes": 64}},
    ]
