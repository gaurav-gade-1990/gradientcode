import numpy as np


def cases():
    rng = np.random.default_rng(41)
    r = lambda *s: rng.normal(size=s)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[1.0, 2.0, 3.0]]), "gamma": np.array([1.0, 1.0, 1.0]), "beta": np.array([0.0, 0.0, 0.0]),
                  "dout": np.array([[1.0, 0.0, 0.0]])},
         "explanation": "The row has mean 2 and biased variance 2/3, so x_hat is about [-1.22, 0, 1.22]."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[0.0, 4.0], [1.0, 1.5]]), "gamma": np.array([2.0, -1.0]), "beta": np.array([0.5, 0.5]),
                  "dout": np.array([[1.0, 1.0], [0.5, -0.5]])},
         "explanation": "Each row is normalized on its own. dgamma and dbeta sum over both rows."},
        {"name": "single vector", "args": {"x": r(6) * 3, "gamma": r(6), "beta": r(6), "dout": r(6)}},
        {"name": "batch of sequences", "args": {"x": r(2, 4, 8) + 1, "gamma": r(8), "beta": r(8), "dout": r(2, 4, 8)}},
        {"name": "square 2d", "args": {"x": r(5, 5) * 2, "gamma": r(5), "beta": r(5), "dout": r(5, 5)}},
        {"name": "tall batch", "args": {"x": r(20, 4), "gamma": r(4), "beta": r(4), "dout": r(20, 4)}},
        {"name": "big eps", "args": {"x": r(3, 6) * 0.1, "gamma": r(6), "beta": r(6), "dout": r(3, 6), "eps": 0.01}},
        {"name": "3d square", "args": {"x": r(3, 3, 3), "gamma": r(3), "beta": r(3), "dout": r(3, 3, 3)}},
    ]
