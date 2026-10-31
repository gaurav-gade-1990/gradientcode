import numpy as np


def cases():
    rng = np.random.default_rng(75)
    I2 = np.eye(2)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([1.0, -1.0]), "W1": I2, "W3": np.array([[2.0, 0.0], [0.0, 3.0]]), "W2": I2},
         "explanation": "gate = SiLU([1, -1]) = [0.7311, -0.2689], value = [2, -3], so the output is [1.4621, 0.8068]."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[0.5, 1.0], [2.0, 0.0]]),
                  "W1": np.array([[1.0, 0.0, -1.0], [0.0, 1.0, 1.0]]),
                  "W3": np.array([[1.0, 1.0, 0.0], [0.0, 1.0, 2.0]]),
                  "W2": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])}},
        {"name": "batch of tokens", "args": {"x": rng.normal(size=(5, 8)), "W1": rng.normal(size=(8, 16)) * 0.5,
                                             "W3": rng.normal(size=(8, 16)) * 0.5, "W2": rng.normal(size=(16, 8)) * 0.5}},
        {"name": "3d input", "args": {"x": rng.normal(size=(2, 3, 4)), "W1": rng.normal(size=(4, 6)),
                                      "W3": rng.normal(size=(4, 6)), "W2": rng.normal(size=(6, 4))}},
        {"name": "large negative gate", "args": {"x": np.array([[10.0, -10.0]]), "W1": np.array([[-2.0, 2.0], [2.0, -2.0]]),
                                                 "W3": np.array([[1.0, 1.0], [1.0, 0.0]]), "W2": np.eye(2)}},
        {"name": "h = 1", "args": {"x": rng.normal(size=(3, 4)), "W1": rng.normal(size=(4, 1)),
                                   "W3": rng.normal(size=(4, 1)), "W2": rng.normal(size=(1, 4))}},
        {"name": "zero input", "args": {"x": np.zeros((2, 3)), "W1": rng.normal(size=(3, 5)),
                                        "W3": rng.normal(size=(3, 5)), "W2": rng.normal(size=(5, 3))}},
    ]
