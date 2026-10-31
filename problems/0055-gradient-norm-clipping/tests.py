import numpy as np


def cases():
    rng = np.random.default_rng(55)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"grads": [np.array([3.0, 0.0]), np.array([[0.0, 4.0]])], "max_norm": 1.0},
         "explanation": "The global norm is sqrt(9 + 16) = 5 > 1, so every array is multiplied by about 1/5."},
        {"name": "Example 2", "hidden": False,
         "args": {"grads": [np.array([0.3, -0.4]), np.array([0.0])], "max_norm": 1.0},
         "explanation": "The global norm is 0.5, already below max_norm, so the gradients come back unchanged."},
        {"name": "many layers clipped", "args": {"grads": [rng.normal(size=(4, 3)), rng.normal(size=3), rng.normal(size=(3, 2)),
                                                           rng.normal(size=2)], "max_norm": 0.5}},
        {"name": "one dominant layer", "args": {"grads": [rng.normal(size=(3, 3)) * 100, rng.normal(size=5) * 0.01],
                                                 "max_norm": 2.0}},
        {"name": "small grads, large max_norm", "args": {"grads": [rng.normal(size=4) * 0.01, rng.normal(size=(2, 2)) * 0.01],
                                                         "max_norm": 5.0}},
        {"name": "all zeros", "args": {"grads": [np.zeros(3), np.zeros((2, 2))], "max_norm": 1.0}},
        {"name": "scalar and 3d arrays", "args": {"grads": [np.array(7.0), rng.normal(size=(2, 3, 2)), np.array([-1.0])],
                                                   "max_norm": 3.0}},
        {"name": "single array just above", "args": {"grads": [np.array([0.6, 0.8001])], "max_norm": 1.0}},
    ]
