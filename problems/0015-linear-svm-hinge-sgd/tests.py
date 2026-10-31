import numpy as np


def cases():
    rng = np.random.default_rng(15)
    Xs = rng.normal(size=(50, 2))
    ys = np.where(Xs @ np.array([1.0, 1.0]) - 0.5 > 0, 1.0, -1.0)
    Xn = rng.normal(size=(120, 4))
    yn = np.where(Xn @ np.array([1.0, -1.0, 0.5, 0.0]) + 0.5 * rng.normal(size=120) + 0.8 > 0, 1.0, -1.0)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[2.0], [1.0], [-1.0], [-3.0]]), "y": np.array([1.0, 1.0, -1.0, -1.0]), "lam": 0.5, "n_iters": 1},
         "explanation": "At w = 0 every margin is 0 < 1, so all samples are active. g_w = -(2 + 1 + 1 + 3) / 4 = -1.75 and g_b = 0. With eta = 1 / (0.5 * 1) = 2, w = [3.5] and b = 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[1.0, 2.0], [2.0, 0.5], [-1.0, -1.5], [0.0, -2.0], [0.5, 0.5]]),
                  "y": np.array([1.0, 1.0, -1.0, -1.0, -1.0]), "lam": 0.1, "n_iters": 50}},
        {"name": "zero iterations", "args": {"X": rng.normal(size=(4, 2)), "y": np.array([1.0, -1.0, 1.0, -1.0]), "lam": 1.0, "n_iters": 0}},
        {"name": "separable", "args": {"X": Xs, "y": ys, "lam": 0.05, "n_iters": 300}},
        {"name": "noisy with offset", "args": {"X": Xn, "y": yn, "lam": 0.01, "n_iters": 400}},
        {"name": "imbalanced labels", "args": {"X": rng.normal(size=(20, 3)), "y": np.array([1.0] * 16 + [-1.0] * 4), "lam": 0.2, "n_iters": 60}},
        {"name": "strong regularization", "args": {"X": Xs, "y": ys, "lam": 5.0, "n_iters": 40}},
        {"name": "few steps", "args": {"X": Xn[:30], "y": yn[:30], "lam": 0.3, "n_iters": 3}},
    ]
