import numpy as np


def cases():
    rng = np.random.default_rng(79)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[1.0, 2.0]]), "W": np.eye(2), "A": np.array([[1.0], [0.0]]),
                  "B": np.array([[0.0, 1.0]]), "alpha": 2.0},
         "explanation": "r = 1, scale = 2. x A = [[1]], (x A) B = [[0, 1]], so y = [[1, 2]] + 2 * [[0, 1]] = [[1, 4]]."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[1.0, 0.0, 1.0], [0.0, 1.0, 0.0]]), "W": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]),
                  "A": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]), "B": np.array([[0.5, 0.0], [0.0, -0.5]]), "alpha": 4.0},
         "explanation": "r = 2, so the LoRA branch is scaled by 4 / 2 = 2."},
        {"name": "B zero init", "args": {"x": rng.normal(size=(3, 5)), "W": rng.normal(size=(5, 4)),
                                         "A": rng.normal(size=(5, 2)), "B": np.zeros((2, 4)), "alpha": 16.0}},
        {"name": "rank 4", "args": {"x": rng.normal(size=(6, 8)), "W": rng.normal(size=(8, 10)),
                                    "A": rng.normal(size=(8, 4)) * 0.1, "B": rng.normal(size=(4, 10)) * 0.1, "alpha": 8.0}},
        {"name": "rank 8 alpha 16", "args": {"x": rng.normal(size=(4, 16)), "W": rng.normal(size=(16, 12)),
                                             "A": rng.normal(size=(16, 8)), "B": rng.normal(size=(8, 12)), "alpha": 16.0}},
        {"name": "rank 1", "args": {"x": rng.normal(size=(2, 3)), "W": rng.normal(size=(3, 3)),
                                    "A": rng.normal(size=(3, 1)), "B": rng.normal(size=(1, 3)), "alpha": 1.0}},
        {"name": "tall output", "args": {"x": rng.normal(size=(5, 4)), "W": rng.normal(size=(4, 9)),
                                         "A": rng.normal(size=(4, 3)), "B": rng.normal(size=(3, 9)), "alpha": 6.0}},
    ]
