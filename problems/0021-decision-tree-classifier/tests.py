import numpy as np


def cases():
    rng = np.random.default_rng(21)
    X2 = rng.uniform(-3, 3, size=(80, 2))
    y2 = ((X2[:, 0] > 0) ^ (X2[:, 1] > 0.5)).astype(int)
    G2 = rng.uniform(-3, 3, size=(60, 2))
    X4 = np.round(rng.normal(size=(150, 4)), 1)
    y4 = np.clip((X4[:, 0] + X4[:, 2] > 0).astype(int) + (X4[:, 3] > 0.8).astype(int) + (rng.random(150) < 0.1), 0, 2).astype(int)
    T4 = np.round(rng.normal(size=(80, 4)), 2)
    Xi = rng.integers(0, 6, size=(40, 3)).astype(float)
    yi = rng.integers(0, 3, size=40)
    Ti = np.vstack([rng.integers(0, 6, size=(20, 3)).astype(float), rng.integers(0, 11, size=(20, 3)) / 2.0])
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X_train": np.array([[1.0], [2.0], [3.0], [4.0], [5.0], [6.0]]), "y_train": np.array([0, 0, 1, 1, 0, 0]),
                  "X_test": np.array([[1.5], [3.5], [5.5], [2.5]]), "max_depth": 2},
         "explanation": "The root splits at 2.5, which ties 4.5 and comes first. The right child {3, 4, 5, 6} splits at 4.5 into {1, 1} and {0, 0}. The test point 2.5 is <= 2.5, so it goes left and gets 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"X_train": np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]), "y_train": np.array([0, 1, 1, 0]),
                  "X_test": np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]), "max_depth": 1},
         "explanation": "XOR. Every root split scores 0.5. Feature 0 at 0.5 comes first. Depth 1 stops there, and both leaves tie 1-1, so they predict the smaller label, 0."},
        {"name": "Example 3", "hidden": False,
         "args": {"X_train": np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]), "y_train": np.array([0, 1, 1, 0]),
                  "X_test": np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]), "max_depth": 2},
         "explanation": "With one more level, each child splits on feature 1 and the tree fits XOR exactly."},
        {"name": "depth zero", "args": {"X_train": X2, "y_train": y2, "X_test": G2[:10], "max_depth": 0}},
        {"name": "xor-like 2d deep", "args": {"X_train": X2, "y_train": y2, "X_test": G2, "max_depth": 6}},
        {"name": "xor-like 2d shallow", "args": {"X_train": X2, "y_train": y2, "X_test": G2, "max_depth": 2}},
        {"name": "min samples split", "args": {"X_train": X4, "y_train": y4, "X_test": T4, "max_depth": 8, "min_samples_split": 20}},
        {"name": "min samples at boundary", "args": {"X_train": np.array([[0.0], [1.0], [2.0], [3.0], [4.0]]), "y_train": np.array([0, 1, 0, 1, 1]),
                                                       "X_test": np.array([[0.2], [1.2], [2.2], [3.2], [4.2]]), "max_depth": 5, "min_samples_split": 2}},
        {"name": "min samples equals node size", "args": {"X_train": np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]]), "y_train": np.array([0, 0, 0, 1, 1, 0]),
                                                            "X_test": np.array([[0.5], [2.5], [3.5], [4.5], [5.0]]), "max_depth": 4, "min_samples_split": 3}},
        {"name": "test on thresholds", "args": {"X_train": Xi, "y_train": yi, "X_test": Ti, "max_depth": 4}},
        {"name": "identical rows different labels", "args": {"X_train": np.array([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0], [2.0, 0.0]]), "y_train": np.array([2, 1, 1, 0]),
                                                              "X_test": np.array([[1.0, 1.0], [2.0, 0.0], [1.5, 0.5]]), "max_depth": 5}},
        {"name": "node-local thresholds", "args": {"X_train": np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 1.0], [10.0, 1.0], [4.0, 5.0], [6.0, 5.0], [5.0, 6.0]]),
                                                    "y_train": np.array([0, 1, 0, 1, 2, 2, 2]),
                                                    "X_test": np.array([[1.0, 0.5], [3.0, 0.5], [4.5, 0.5], [5.5, 0.5], [7.0, 0.5], [9.0, 0.5]]), "max_depth": 3}},
        {"name": "multiclass deep", "args": {"X_train": X4, "y_train": y4, "X_test": T4, "max_depth": 10}},
    ]
