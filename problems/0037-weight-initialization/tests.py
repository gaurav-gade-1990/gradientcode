import numpy as np


def _case(rng, fi, fo):
    return {"fan_in": fi, "fan_out": fo, "u": rng.random((fi, fo)), "z": rng.standard_normal((fi, fo))}


def cases():
    rng = np.random.default_rng(37)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"fan_in": 2, "fan_out": 1, "u": np.array([[0.0], [0.75]]), "z": np.array([[1.0], [-0.5]])},
         "explanation": "a = sqrt(6 / 3) = 1.414, so u = 0 maps to -a and u = 0.75 maps to a / 2. sigma = sqrt(2 / 2) = 1."},
        {"name": "Example 2", "hidden": False,
         "args": {"fan_in": 3, "fan_out": 3, "u": np.array([[0.5, 0.25, 0.9], [0.1, 0.5, 0.0], [0.99, 0.6, 0.3]]),
                  "z": np.array([[0.0, 1.0, -1.0], [2.0, -2.0, 0.5], [0.3, -0.3, 1.5]])}},
        {"name": "wide layer", "args": _case(rng, 4, 16)},
        {"name": "tall layer", "args": _case(rng, 32, 4)},
        {"name": "single weight", "args": _case(rng, 1, 1)},
        {"name": "big fan in", "args": _case(rng, 128, 2)},
        {"name": "rectangular", "args": _case(rng, 10, 30)},
    ]
