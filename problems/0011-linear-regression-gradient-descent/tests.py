import numpy as np


def cases():
    rng = np.random.default_rng(11)
    X3 = rng.normal(size=(40, 3))
    y3 = X3 @ np.array([1.5, -2.0, 0.5]) + 4.0 + 0.1 * rng.normal(size=40)
    X5 = rng.normal(size=(120, 5))
    y5 = X5 @ rng.normal(size=5) - 1.0 + 0.3 * rng.normal(size=120)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[1.0], [2.0], [3.0]]), "y": np.array([2.0, 4.0, 6.0]), "lr": 0.1, "n_iters": 1},
         "explanation": "From zero, r = -y. dw = (2/3) * (1*-2 + 2*-4 + 3*-6) = -56/3 and db = (2/3) * -12 = -8. After one step w = [1.8667] and b = 0.8."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [2.0, 2.0]]), "y": np.array([1.0, 2.0, 3.5, 6.0]),
                  "lr": 0.05, "n_iters": 200}},
        {"name": "zero iterations", "args": {"X": rng.normal(size=(5, 2)), "y": rng.normal(size=5), "lr": 0.1, "n_iters": 0}},
        {"name": "three features converge", "args": {"X": X3, "y": y3, "lr": 0.05, "n_iters": 500}},
        {"name": "few steps", "args": {"X": X3, "y": y3, "lr": 0.1, "n_iters": 3}},
        {"name": "bigger problem", "args": {"X": X5, "y": y5, "lr": 0.02, "n_iters": 300}},
        {"name": "offset only", "args": {"X": np.zeros((6, 1)), "y": np.full(6, 7.0), "lr": 0.25, "n_iters": 10}},
        {"name": "diverging lr", "args": {"X": np.array([[1.0], [2.0], [3.0], [4.0]]), "y": np.array([1.0, 2.0, 2.0, 5.0]), "lr": 0.2, "n_iters": 15}},
    ]
