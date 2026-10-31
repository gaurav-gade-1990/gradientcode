import numpy as np


def cases():
    rng = np.random.default_rng(34)
    return [
        {"name": "Example 1", "hidden": False, "args": {"x": np.array([-2.0, 0.0, 2.0])},
         "explanation": "At x = 0: sigmoid = 0.5 with slope 0.25, tanh = 0 with slope 1, relu' = 0, leaky' = alpha, gelu = 0 with slope 0.5."},
        {"name": "Example 2", "hidden": False, "args": {"x": np.array([[-1.0, 0.5], [3.0, -0.1]]), "alpha": 0.2}},
        {"name": "exact zeros", "args": {"x": np.array([0.0, -0.0, 0.0, 1e-12, -1e-12])}},
        {"name": "extreme inputs", "args": {"x": np.array([-1000.0, -50.0, 50.0, 1000.0])}},
        {"name": "random 3d", "args": {"x": rng.normal(size=(2, 3, 4)) * 3}},
        {"name": "alpha zero", "args": {"x": rng.normal(size=10), "alpha": 0.0}},
        {"name": "gelu region", "args": {"x": np.linspace(-4, 4, 17)}},
        {"name": "scalar-like", "args": {"x": np.array([0.7])}},
    ]
