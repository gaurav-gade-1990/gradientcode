import numpy as np


def cases():
    rng = np.random.default_rng(16)
    centers = np.array([[0.0, 0.0], [4.0, 0.0], [0.0, 4.0]])
    yb = rng.integers(0, 3, size=60)
    Xb = centers[yb] + rng.normal(size=(60, 2))
    Xt = rng.uniform(-1, 5, size=(25, 2))
    # integer grid with many exact distance ties
    Xg = rng.integers(0, 4, size=(30, 2)).astype(float)
    yg = rng.integers(0, 4, size=30)
    Xgt = rng.integers(0, 4, size=(20, 2)).astype(float)
    Xl = rng.normal(size=(200, 6))
    yl = rng.integers(0, 10, size=200)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X_train": np.array([[0.0], [1.0], [2.0], [10.0], [11.0]]), "y_train": np.array([0, 0, 1, 1, 1]),
                  "X_test": np.array([[0.4], [9.0]]), "k": 3},
         "explanation": "For 0.4 the nearest three are x = 0, 1, 2 with labels 0, 0, 1, so the prediction is 0. For 9.0 they are 10, 11, 2, all labeled 1."},
        {"name": "Example 2", "hidden": False,
         "args": {"X_train": np.array([[0.0, 0.0], [3.0, 0.0], [0.0, 2.0], [5.0, 5.0]]), "y_train": np.array([2, 1, 1, 2]),
                  "X_test": np.array([[1.0, 0.0]]), "k": 2},
         "explanation": "The two nearest are (0, 0) at distance 1 (label 2) and (3, 0) at distance 2 (label 1). Labels 1 and 2 tie with one vote each, so take the nearest neighbor's label: 2."},
        {"name": "k equals 1", "args": {"X_train": Xb, "y_train": yb, "X_test": Xt, "k": 1}},
        {"name": "three blobs k=5", "args": {"X_train": Xb, "y_train": yb, "X_test": Xt, "k": 5}},
        {"name": "even k ties", "args": {"X_train": Xb, "y_train": yb, "X_test": Xt, "k": 4}},
        {"name": "grid distance ties", "args": {"X_train": Xg, "y_train": yg, "X_test": Xgt, "k": 4}},
        {"name": "distance tie at boundary", "args": {"X_train": np.array([[1.0], [-1.0], [2.0], [-2.0]]), "y_train": np.array([3, 5, 5, 3]),
                                                       "X_test": np.array([[0.0]]), "k": 1}},
        {"name": "k equals n", "args": {"X_train": Xg[:7], "y_train": yg[:7], "X_test": Xgt, "k": 7}},
        {"name": "larger", "args": {"X_train": Xl, "y_train": yl, "X_test": rng.normal(size=(60, 6)), "k": 6}},
    ]
