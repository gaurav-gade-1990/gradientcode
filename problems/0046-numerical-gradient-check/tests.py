import numpy as np


def _softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


def cases():
    rng = np.random.default_rng(46)
    x1 = np.array([1.0, -2.0, 0.5])
    x3 = rng.normal(size=(3, 4))
    x4 = rng.normal(size=6) * 2
    x5 = rng.normal(size=(2, 3))
    x6 = rng.normal(size=8)
    x7 = rng.normal(size=(2, 2, 3))
    x8 = rng.normal(size=5) * 3
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"expr": "np.sum(x ** 2)", "x": x1, "analytic_grad": 2 * x1},
         "explanation": "f = sum(x^2) has gradient 2x. Central differences are exact for a quadratic, so rel_error is about 0 (only rounding error)."},
        {"name": "Example 2", "hidden": False,
         "args": {"expr": "np.sum(x ** 3)", "x": np.array([1.0, 2.0]), "analytic_grad": np.array([2.0, 4.0])},
         "explanation": "The analytic gradient is wrong (2x instead of 3x^2 = [3, 12]), and rel_error is large."},
        {"name": "sin times x, 2d", "args": {"expr": "np.sum(np.sin(x) * x)", "x": x3, "analytic_grad": np.cos(x3) * x3 + np.sin(x3)}},
        {"name": "log-sum-exp", "args": {"expr": "np.log(np.sum(np.exp(x)))", "x": x4, "analytic_grad": _softmax(x4)}},
        {"name": "matrix quartic", "args": {"expr": "np.sum((x @ x.T) ** 2)", "x": x5, "analytic_grad": 4 * (x5 @ x5.T) @ x5}},
        {"name": "wrong sign", "args": {"expr": "np.sum(np.exp(x)) * 0.1", "x": x6, "analytic_grad": -0.1 * np.exp(x6)}},
        {"name": "3d tanh", "args": {"expr": "np.sum(np.tanh(x) ** 2)", "x": x7, "analytic_grad": 2 * np.tanh(x7) * (1 - np.tanh(x7) ** 2)}},
        {"name": "slightly off grad", "args": {"expr": "np.sum(x ** 4) / 10", "x": x8, "analytic_grad": 0.4 * x8 ** 3 + 0.5}},
        {"name": "coupled terms", "args": {"expr": "np.sum(x[:-1] * x[1:]) + np.sum(x ** 3)", "x": x6,
                                            "analytic_grad": np.r_[x6[1:], 0] + np.r_[0, x6[:-1]] + 3 * x6 ** 2}},
        {"name": "bigger step", "args": {"expr": "np.sum(np.cos(x))", "x": x4, "analytic_grad": -np.sin(x4), "h": 1e-3}},
    ]
