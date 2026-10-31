import numpy as np


def cases():
    rng = np.random.default_rng(13)
    n = 80
    X2 = rng.normal(size=(n, 2))
    y2 = (X2 @ np.array([2.0, -1.0]) + 0.5 + 0.5 * rng.normal(size=n) > 0).astype(float)
    X5 = rng.normal(size=(150, 5))
    y5 = (rng.random(150) < 1 / (1 + np.exp(-(X5 @ rng.normal(size=5))))).astype(float)
    Xbig = np.array([[1000.0], [2000.0], [-1500.0], [-500.0]])
    ybig = np.array([1.0, 1.0, 0.0, 0.0])
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[1.0], [2.0], [-1.0], [-2.0]]), "y": np.array([1.0, 1.0, 0.0, 0.0]), "lr": 0.5, "n_iters": 1},
         "explanation": "At w = 0 every p is 0.5, so p - y = [-0.5, -0.5, 0.5, 0.5]. dw = (-0.5 - 1 - 0.5 - 1) / 4 = -0.75 and db = 0. After one step w = [0.375] and b = 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [2.0, 2.0], [0.0, 0.0]]),
                  "y": np.array([0.0, 0.0, 1.0, 1.0, 0.0]), "lr": 0.3, "n_iters": 100}},
        {"name": "zero iterations", "args": {"X": rng.normal(size=(4, 3)), "y": np.array([0.0, 1.0, 1.0, 0.0]), "lr": 1.0, "n_iters": 0}},
        {"name": "noisy 2d", "args": {"X": X2, "y": y2, "lr": 0.1, "n_iters": 400}},
        {"name": "five features", "args": {"X": X5, "y": y5, "lr": 0.2, "n_iters": 250}},
        {"name": "huge logits", "args": {"X": Xbig, "y": ybig, "lr": 0.1, "n_iters": 20}},
        {"name": "all one class", "args": {"X": rng.normal(size=(10, 2)), "y": np.ones(10), "lr": 0.5, "n_iters": 50}},
        {"name": "separable large scale", "args": {"X": np.array([[300.0, 1.0], [250.0, -2.0], [-200.0, 0.5], [-350.0, 3.0], [100.0, 0.0]]),
                                                    "y": np.array([1.0, 1.0, 0.0, 0.0, 0.0]), "lr": 0.05, "n_iters": 30}},
    ]
