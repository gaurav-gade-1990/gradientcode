import numpy as np


def cases():
    rng = np.random.default_rng(50)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"param": np.array([1.0, -2.0, 3.0]), "grad": np.array([0.5, -4.0, 2.0]), "state_sum": np.zeros(3), "lr": 0.1},
         "explanation": "On the first step state_sum = g^2, so g / sqrt(state_sum) = sign(g). Every parameter moves by 0.1 against its gradient's sign."},
        {"name": "Example 2", "hidden": False,
         "args": {"param": np.array([0.0, 0.0]), "grad": np.array([3.0, 3.0]), "state_sum": np.array([0.0, 16.0]), "lr": 1.0},
         "explanation": "state_sum = [9, 25]. The steps are 3/3 = 1 and 3/5 = 0.6: the element with more gradient history moves less."},
        {"name": "random history", "args": {"param": rng.normal(size=6), "grad": rng.normal(size=6),
                                             "state_sum": rng.random(6) * 4}},
        {"name": "tiny gradient, large eps", "args": {"param": rng.normal(size=5), "grad": np.full(5, 1e-4),
                                                       "state_sum": np.zeros(5), "eps": 1e-3, "lr": 0.1}},
        {"name": "weight decay first step", "args": {"param": rng.normal(size=(3, 4)), "grad": rng.normal(size=(3, 4)),
                                                      "state_sum": np.zeros((3, 4)), "lr": 0.05, "weight_decay": 0.5}},
        {"name": "weight decay with history", "args": {"param": rng.normal(size=6) * 3, "grad": rng.normal(size=6),
                                                        "state_sum": rng.random(6), "lr": 0.1, "weight_decay": 0.2}},
        {"name": "zero gradient with history", "args": {"param": np.array([1.0, 2.0]), "grad": np.zeros(2),
                                                         "state_sum": np.array([1.0, 4.0])}},
        {"name": "long history matrix", "args": {"param": rng.normal(size=(4, 5)), "grad": rng.normal(size=(4, 5)),
                                                  "state_sum": rng.random((4, 5)) * 100, "lr": 0.5}},
    ]
