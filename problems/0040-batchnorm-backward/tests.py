import numpy as np


def cases():
    rng = np.random.default_rng(40)
    r = lambda *s: rng.normal(size=s)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"dout": np.array([[1.0], [0.0], [-1.0]]), "x": np.array([[1.0], [2.0], [3.0]]), "gamma": np.array([1.0])},
         "explanation": "x_hat is about [-1.22, 0, 1.22], so dgamma = -2.45 and dbeta = 0. dout points exactly along -x_hat, a direction normalization cancels, so dx is about 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"dout": np.array([[1.0, 2.0], [0.5, -1.0]]), "x": np.array([[0.0, 1.0], [2.0, 5.0]]), "gamma": np.array([2.0, 0.5])},
         "explanation": "With N = 2, x_hat is about +-1 and dx is close to 0: two points can only shift and scale."},
        {"name": "random 2d", "args": {"dout": r(8, 5), "x": r(8, 5) * 3 + 2, "gamma": r(5)}},
        {"name": "random 4d", "args": {"dout": r(2, 3, 4, 4), "x": r(2, 3, 4, 4) * 2 - 1, "gamma": r(3)}},
        {"name": "4d single sample", "args": {"dout": r(1, 2, 3, 3), "x": r(1, 2, 3, 3), "gamma": r(2)}},
        {"name": "4d non-square spatial", "args": {"dout": r(3, 4, 2, 5), "x": r(3, 4, 2, 5), "gamma": r(4)}},
        {"name": "big eps", "args": {"dout": r(6, 3), "x": r(6, 3) * 0.1, "gamma": r(3), "eps": 0.05}},
        {"name": "large batch", "args": {"dout": r(64, 4), "x": r(64, 4) * 5, "gamma": r(4)}},
    ]
