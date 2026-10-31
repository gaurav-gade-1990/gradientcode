import numpy as np


def cases():
    rng = np.random.default_rng(49)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"param": np.array([1.0, -2.0]), "grad": np.array([1.0, 2.0]), "buf": np.zeros(2), "lr": 0.1},
         "explanation": "buf = g = [1, 2]. The step is g + 0.9 * buf = 1.9 * g, so param = [1, -2] - 0.19 * [1, 2] = [0.81, -2.38]."},
        {"name": "Example 2", "hidden": False,
         "args": {"param": np.array([0.0, 1.0, 2.0]), "grad": np.array([0.5, 0.0, -0.5]), "buf": np.array([1.0, 1.0, 1.0]),
                  "lr": 0.1, "momentum": 0.5},
         "explanation": "buf = 0.5 * 1 + g = [1, 0.5, 0]. The step is g + 0.5 * buf = [1, 0.25, -0.5]."},
        {"name": "random state", "args": {"param": rng.normal(size=6), "grad": rng.normal(size=6),
                                           "buf": rng.normal(size=6), "lr": 0.05}},
        {"name": "zero momentum is plain SGD", "args": {"param": rng.normal(size=4), "grad": rng.normal(size=4),
                                                         "buf": rng.normal(size=4), "momentum": 0.0, "lr": 0.3}},
        {"name": "weight decay", "args": {"param": rng.normal(size=(3, 4)), "grad": rng.normal(size=(3, 4)),
                                           "buf": rng.normal(size=(3, 4)), "lr": 0.1, "momentum": 0.9, "weight_decay": 0.1}},
        {"name": "zero gradient, buffer coasts", "args": {"param": np.array([1.0, -1.0]), "grad": np.zeros(2),
                                                         "buf": np.array([2.0, -3.0]), "lr": 0.1, "momentum": 0.8}},
        {"name": "high momentum matrix", "args": {"param": rng.normal(size=(5, 5)), "grad": rng.normal(size=(5, 5)),
                                                   "buf": rng.normal(size=(5, 5)) * 5, "lr": 1e-3, "momentum": 0.99}},
    ]
