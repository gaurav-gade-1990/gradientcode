import numpy as np


def cases():
    rng = np.random.default_rng(14)
    X_sep = rng.normal(size=(40, 2))
    y_sep = np.where(X_sep @ np.array([1.0, -2.0]) + 0.3 > 0, 1.0, -1.0)
    X_noisy = rng.normal(size=(60, 3))
    y_noisy = np.where(X_noisy @ np.array([0.5, 1.0, -1.0]) + 0.4 * rng.normal(size=60) > 0, 1.0, -1.0)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[2.0, 1.0], [-1.0, -1.0], [1.0, 2.0]]), "y": np.array([1.0, -1.0, 1.0]), "n_epochs": 1},
         "explanation": "Sample 0 scores 0, which counts as a mistake: w = [2, 1], b = 1. Sample 1 scores -1*(-2 - 1 + 1) = 2 > 0, so no update. Sample 2 scores 1*(2 + 2 + 1) = 5 > 0, so no update."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[1.0], [3.0], [-1.0], [-2.0]]), "y": np.array([-1.0, 1.0, 1.0, -1.0]), "n_epochs": 3, "lr": 0.5}},
        {"name": "zero epochs", "args": {"X": rng.normal(size=(5, 2)), "y": np.array([1.0, -1.0, 1.0, 1.0, -1.0]), "n_epochs": 0}},
        {"name": "separable many epochs", "args": {"X": X_sep, "y": y_sep, "n_epochs": 30}},
        {"name": "noisy data", "args": {"X": X_noisy, "y": y_noisy, "n_epochs": 10, "lr": 0.1}},
        {"name": "xor never converges", "args": {"X": np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]),
                                                  "y": np.array([-1.0, 1.0, 1.0, -1.0]), "n_epochs": 7}},
        {"name": "single sample", "args": {"X": np.array([[0.5, -0.5, 2.0]]), "y": np.array([-1.0]), "n_epochs": 4}},
        {"name": "order matters", "args": {"X": np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, -1.0], [2.0, -1.0], [-1.0, 2.0]]),
                                            "y": np.array([1.0, -1.0, -1.0, 1.0, -1.0]), "n_epochs": 5}},
    ]
