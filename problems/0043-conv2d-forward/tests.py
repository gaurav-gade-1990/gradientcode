import numpy as np


def cases():
    rng = np.random.default_rng(43)
    r = lambda *s: rng.normal(size=s)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.arange(1.0, 10.0).reshape(1, 1, 3, 3), "w": np.array([[[[1.0, 0.0], [0.0, -1.0]]]]), "b": np.array([0.5])},
         "explanation": "Each output is x[y, z] - x[y + 1, z + 1] + 0.5 = 1 - 5 + 0.5 = -3.5 everywhere."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[[[1.0, 2.0], [3.0, 4.0]], [[0.0, 1.0], [1.0, 0.0]]]]),
                  "w": np.array([[[[1.0]], [[10.0]]], [[[0.0]], [[-1.0]]]]), "b": np.array([0.0, 1.0]), "pad": 1},
         "explanation": "1x1 filters mix channels: filter 0 gives x0 + 10 * x1, filter 1 gives 1 - x1. Padding adds a ring of bias-only outputs."},
        {"name": "random 3x3 pad 1", "args": {"x": r(2, 3, 5, 5), "w": r(4, 3, 3, 3), "b": r(4), "pad": 1}},
        {"name": "stride 2 with leftover", "args": {"x": r(2, 2, 6, 7), "w": r(3, 2, 3, 3), "b": r(3), "stride": 2}},
        {"name": "non-square kernel", "args": {"x": r(1, 2, 5, 6), "w": r(2, 2, 2, 3), "b": r(2), "stride": 1, "pad": 2}},
        {"name": "stride 3", "args": {"x": r(3, 1, 8, 8), "w": r(2, 1, 2, 2), "b": r(2), "stride": 3, "pad": 1}},
        {"name": "full-size kernel", "args": {"x": r(4, 2, 3, 3), "w": r(5, 2, 3, 3), "b": r(5)}},
        {"name": "many channels", "args": {"x": r(2, 8, 6, 6), "w": r(6, 8, 3, 3), "b": r(6), "stride": 2, "pad": 1}},
    ]
