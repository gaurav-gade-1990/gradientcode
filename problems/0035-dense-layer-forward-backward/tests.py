import numpy as np


def cases():
    rng = np.random.default_rng(35)
    r = lambda *s: rng.normal(size=s)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[1.0, 2.0]]), "W": np.array([[1.0, 0.0, -1.0], [0.5, 2.0, 1.0]]),
                  "b": np.array([0.1, 0.2, 0.3]), "dout": np.array([[1.0, 0.0, -1.0]])},
         "explanation": "out = [1 + 1 + 0.1, 4 + 0.2, -1 + 2 + 0.3]. dW = x.T @ dout is an outer product, and db = dout."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]), "W": np.array([[2.0, -1.0], [0.5, 3.0]]),
                  "b": np.array([0.0, 1.0]), "dout": np.array([[1.0, 1.0], [0.0, 2.0], [-1.0, 0.5]])},
         "explanation": "db sums dout over the 3 rows: [0, 3.5]."},
        {"name": "batch of sequences", "args": {"x": r(2, 3, 4), "W": r(4, 5), "b": r(5), "dout": r(2, 3, 5)}},
        {"name": "single vector", "args": {"x": r(4), "W": r(4, 3), "b": r(3), "dout": r(3)}},
        {"name": "square but non-symmetric", "args": {"x": r(6, 3), "W": r(3, 3), "b": r(3), "dout": r(6, 3)}},
        {"name": "tall batch", "args": {"x": r(32, 8), "W": r(8, 2), "b": r(2), "dout": r(32, 2)}},
        {"name": "one output unit", "args": {"x": r(5, 7), "W": r(7, 1), "b": r(1), "dout": r(5, 1)}},
        {"name": "3d square", "args": {"x": r(3, 2, 4), "W": r(4, 4), "b": r(4), "dout": r(3, 2, 4)}},
    ]
