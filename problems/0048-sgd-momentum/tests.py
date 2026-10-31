import numpy as np


def cases():
    rng = np.random.default_rng(48)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"param": np.array([1.0, -2.0, 3.0]), "grad": np.array([0.5, -1.0, 2.0]), "buf": np.zeros(3), "lr": 0.1},
         "explanation": "On the first step the buffer is zero, so buf = grad and param moves by -lr * grad."},
        {"name": "Example 2", "hidden": False,
         "args": {"param": np.array([0.5, 0.5]), "grad": np.array([1.0, -1.0]), "buf": np.array([2.0, 1.0]),
                  "lr": 0.1, "momentum": 0.5},
         "explanation": "buf = 0.5 * [2, 1] + [1, -1] = [2, -0.5]; param = [0.5, 0.5] - 0.1 * buf = [0.3, 0.55]."},
        {"name": "Example 3", "hidden": False,
         "args": {"param": np.array([2.0, -1.0]), "grad": np.array([0.0, 0.0]), "buf": np.zeros(2),
                  "lr": 0.5, "momentum": 0.9, "weight_decay": 0.1},
         "explanation": "With a zero gradient, weight decay alone gives g = 0.1 * param, which shrinks param toward 0."},
        {"name": "nonzero buffer, default momentum", "args": {"param": rng.normal(size=6), "grad": rng.normal(size=6),
                                                              "buf": rng.normal(size=6), "lr": 0.05}},
        {"name": "zero momentum is plain SGD", "args": {"param": rng.normal(size=5), "grad": rng.normal(size=5),
                                                         "buf": rng.normal(size=5), "momentum": 0.0, "lr": 0.2}},
        {"name": "weight decay with history", "args": {"param": rng.normal(size=(3, 4)), "grad": rng.normal(size=(3, 4)),
                                                        "buf": rng.normal(size=(3, 4)), "lr": 0.1, "momentum": 0.9,
                                                        "weight_decay": 0.05}},
        {"name": "matrix param", "args": {"param": rng.normal(size=(5, 5)), "grad": rng.normal(size=(5, 5)) * 3,
                                           "buf": rng.normal(size=(5, 5)), "lr": 1e-3, "momentum": 0.99}},
        {"name": "zero gradient, momentum coasts", "args": {"param": np.array([1.0, 2.0]), "grad": np.zeros(2),
                                                            "buf": np.array([0.4, -0.4]), "lr": 0.1}},
    ]
