import numpy as np


def cases():
    rng = np.random.default_rng(51)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"param": np.array([1.0, -1.0]), "grad": np.array([2.0, -2.0]), "square_avg": np.zeros(2),
                  "lr": 0.1, "alpha": 0.75},
         "explanation": "square_avg = 0.25 * 4 = [1, 1], so the step is 0.1 * g / 1 = [0.2, -0.2]."},
        {"name": "Example 2", "hidden": False,
         "args": {"param": np.array([0.0, 0.0, 0.0]), "grad": np.array([1.0, 1.0, 1.0]),
                  "square_avg": np.array([0.0, 1.0, 4.0]), "lr": 0.1, "alpha": 0.5},
         "explanation": "square_avg = 0.5 * [0, 1, 4] + 0.5 = [0.5, 1, 2.5]. The parameter with the largest history moves least."},
        {"name": "default alpha with history", "args": {"param": rng.normal(size=6), "grad": rng.normal(size=6),
                                                         "square_avg": rng.random(6)}},
        {"name": "tiny gradient, large eps", "args": {"param": rng.normal(size=5), "grad": np.full(5, 1e-4),
                                                       "square_avg": np.full(5, 1e-8), "eps": 1e-3, "lr": 0.1}},
        {"name": "weight decay", "args": {"param": rng.normal(size=(3, 4)), "grad": rng.normal(size=(3, 4)),
                                           "square_avg": rng.random((3, 4)) * 0.1, "lr": 0.01, "weight_decay": 0.1}},
        {"name": "zero gradient", "args": {"param": np.array([1.0, -2.0]), "grad": np.zeros(2),
                                            "square_avg": np.array([0.5, 0.2])}},
        {"name": "first step, alpha 0.9", "args": {"param": rng.normal(size=(4, 4)), "grad": rng.normal(size=(4, 4)) * 10,
                                                    "square_avg": np.zeros((4, 4)), "alpha": 0.9, "lr": 1e-3}},
    ]
