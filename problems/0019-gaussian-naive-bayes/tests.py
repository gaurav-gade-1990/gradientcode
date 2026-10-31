import numpy as np


def cases():
    rng = np.random.default_rng(19)
    mus = np.array([[0.0, 0.0, 0.0], [2.0, -1.0, 1.0], [-2.0, 2.0, 0.5]])
    yb = rng.integers(0, 3, size=90)
    Xb = mus[yb] + rng.normal(size=(90, 3)) * np.array([1.0, 0.5, 2.0])
    Xc = rng.normal(size=(20, 2))
    Xc[:10, 1] = 5.0
    yc = np.array([0] * 10 + [1] * 10)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X_train": np.array([[1.0], [2.0], [3.0], [7.0], [8.0], [9.0]]), "y_train": np.array([0, 0, 0, 1, 1, 1]),
                  "X_test": np.array([[2.5], [5.0], [8.5]])},
         "explanation": "Class 0 has mean 2 and class 1 has mean 8. Both have variance 2/3 (plus a tiny epsilon) and prior 0.5. The test point 5.0 is equidistant, so its posterior is [log 0.5, log 0.5] and the tie goes to class 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"X_train": np.array([[0.0, 1.0], [1.0, 1.0], [0.0, 3.0], [4.0, 4.0], [5.0, 6.0]]), "y_train": np.array([3, 3, 3, 7, 7]),
                  "X_test": np.array([[0.5, 2.0], [4.0, 5.0]])},
         "explanation": "The labels need not start at 0. Columns of log_post follow the sorted classes [3, 7]."},
        {"name": "three classes 3d", "args": {"X_train": Xb, "y_train": yb, "X_test": rng.normal(size=(30, 3)) * 2}},
        {"name": "small classes", "args": {"X_train": np.array([[0.0, 0.0], [1.0, 2.0], [3.0, 1.0], [4.0, 3.0], [-2.0, 5.0], [-1.0, 4.0], [0.5, 0.5]]),
                                            "y_train": np.array([0, 0, 1, 1, 2, 2, 2]), "X_test": np.array([[0.0, 1.0], [3.5, 2.0], [-1.5, 4.5], [10.0, -10.0]])}},
        {"name": "constant feature within a class", "args": {"X_train": Xc, "y_train": yc, "X_test": np.array([[0.0, 5.0], [0.3, 4.0], [-1.0, 0.0]])}},
        {"name": "far test points", "args": {"X_train": Xb, "y_train": yb, "X_test": np.array([[300.0, -200.0, 500.0], [-1000.0, 1000.0, 0.0]])}},
        {"name": "larger smoothing", "args": {"X_train": Xb, "y_train": yb, "X_test": Xb[:15], "var_smoothing": 0.5}},
        {"name": "single class", "args": {"X_train": Xb[:12], "y_train": np.full(12, 4), "X_test": Xb[12:16]}},
    ]
