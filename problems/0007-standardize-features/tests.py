import numpy as np


def cases():
    rng = np.random.default_rng(7)
    scales = np.array([1.0, 100.0, 0.01, 5.0])
    shift = np.array([0.0, -50.0, 3.0, 1000.0])
    Xtr = rng.normal(size=(30, 4)) * scales + shift
    Xte = rng.normal(size=(10, 4)) * scales * 2 + shift + 1.0
    const_tr = np.column_stack([rng.normal(size=8), np.full(8, 3.0), rng.normal(size=8) * 4])
    const_te = np.column_stack([rng.normal(size=5), np.array([3.0, 4.0, 2.0, 3.0, 10.0]), rng.normal(size=5)])
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X_train": np.array([[1.0, 10.0], [3.0, 10.0]]), "X_test": np.array([[2.0, 12.0], [5.0, 10.0]])},
         "explanation": "Column 1 has mean 2 and std 1. Column 2 is constant (std 0, treated as 1), so it is only centered: 12 maps to 2."},
        {"name": "Example 2", "hidden": False,
         "args": {"X_train": np.array([[0.0], [2.0], [4.0], [6.0]]), "X_test": np.array([[8.0]])},
         "explanation": "Mean 3, population std sqrt(5). The test value uses the training statistics: (8 - 3) / sqrt(5)."},
        {"name": "different scales and shifts", "args": {"X_train": Xtr, "X_test": Xte}},
        {"name": "constant column in train", "args": {"X_train": const_tr, "X_test": const_te}},
        {"name": "single training row", "args": {"X_train": np.array([[1.0, -2.0, 3.0]]), "X_test": np.array([[0.0, 0.0, 0.0], [1.0, -2.0, 4.0]])}},
        {"name": "empty test set", "args": {"X_train": rng.normal(size=(6, 3)), "X_test": np.zeros((0, 3))}},
        {"name": "test equals train", "args": {"X_train": Xtr[:12], "X_test": Xtr[:12].copy()}},
        {"name": "larger", "args": {"X_train": rng.exponential(size=(200, 10)), "X_test": rng.exponential(size=(50, 10)) * 3}},
    ]
