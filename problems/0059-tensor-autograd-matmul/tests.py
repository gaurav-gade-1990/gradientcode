import numpy as np


def _r(rng, *shape):
    return np.round(rng.normal(size=shape), 3)


MLP = "((d := (x @ W1 + b1).relu() @ W2 + b2 - y) * d).mean()"


def cases():
    rng = np.random.default_rng(59)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"expr": "(x @ w).sum()",
                  "inputs": {"x": np.array([[1.0, 2.0], [3.0, 4.0]]), "w": np.array([[1.0], [-1.0]])}},
         "explanation": "x @ w = [[-1], [-1]], so the loss is -2. With G = ones((2, 1)): dx = G @ w.T = [[1, -1], [1, -1]] and dw = x.T @ G = [[4], [6]]."},
        {"name": "Example 2", "hidden": False,
         "args": {"expr": "(x + b).relu().mean()",
                  "inputs": {"x": np.array([[1.0, -2.0, 3.0], [-1.0, 0.5, -3.0]]), "b": np.array([0.5, 1.0, -1.0])}},
         "explanation": "b of shape (3,) is broadcast over both rows, so db sums the row gradients. Each live element passes 1/6; db = [1/6, 1/6, 1/6]."},
        {"name": "Example 3", "hidden": False,
         "args": {"expr": "(x * x * s).sum() + 1",
                  "inputs": {"x": np.array([1.0, -2.0, 3.0]), "s": np.array(0.5)}},
         "explanation": "x is used twice, so dx = 2 * s * x = [1, -2, 3]. s is a 0-d Tensor broadcast everywhere: ds = sum(x^2) = 14."},
        {"name": "two-layer MLP, MSE loss",
         "args": {"expr": MLP, "inputs": {"x": _r(rng, 4, 3), "W1": _r(rng, 3, 5), "b1": _r(rng, 5),
                                          "W2": _r(rng, 5, 2), "b2": _r(rng, 2), "y": _r(rng, 4, 2)}}},
        {"name": "MLP with column-vector bias",
         "args": {"expr": "((x @ W1 + c).relu() @ W2).mean() * 3",
                  "inputs": {"x": _r(rng, 6, 4), "W1": _r(rng, 4, 3), "c": _r(rng, 6, 1), "W2": _r(rng, 3, 2)}}},
        {"name": "three layers, shared weight",
         "args": {"expr": "((x @ W + b).relu() @ W + b).relu().sum()",
                  "inputs": {"x": _r(rng, 5, 4), "W": _r(rng, 4, 4), "b": _r(rng, 1, 4)}}},
        {"name": "branch reuse",
         "args": {"expr": "((h := (x @ A).relu()) @ B).sum() + (h * h).mean()",
                  "inputs": {"x": _r(rng, 3, 4), "A": _r(rng, 4, 5), "B": _r(rng, 5, 2)}}},
        {"name": "relu exactly at zero",
         "args": {"expr": "(x.relu() * w).sum()",
                  "inputs": {"x": np.array([[0.0, 1.0], [-1.0, 0.0]]), "w": np.array([[2.0, 3.0], [4.0, 5.0]])}}},
        {"name": "scalar constants on both sides",
         "args": {"expr": "(1 - 2 * x + x * 3).relu().mean() - (0.5 * y).sum()",
                  "inputs": {"x": _r(rng, 3, 3), "y": _r(rng, 3)}}},
        {"name": "sum vs mean scale",
         "args": {"expr": "(x @ W).mean() + (x @ W).sum() * 0.1",
                  "inputs": {"x": _r(rng, 8, 3), "W": _r(rng, 3, 6)}}},
        {"name": "x @ x.T style reuse",
         "args": {"expr": "(a @ b @ a).sum()", "inputs": {"a": _r(rng, 3, 3), "b": _r(rng, 3, 3)}}},
        {"name": "scalar tensor gate",
         "args": {"expr": "((x @ W) * g + g).relu().sum()",
                  "inputs": {"x": _r(rng, 4, 3), "W": _r(rng, 3, 2), "g": np.array(0.7)}}},
    ]
