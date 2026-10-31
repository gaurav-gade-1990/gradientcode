import numpy as np


def _sigmoid(x):
    # exp of a non-positive number never overflows.
    e = np.exp(-np.abs(x))
    return np.where(x >= 0, 1.0 / (1.0 + e), e / (1.0 + e))


def activations(x: np.ndarray, alpha: float = 0.01) -> dict:
    x = np.asarray(x, dtype=float)
    s = _sigmoid(x)
    t = np.tanh(x)
    pos = x > 0

    c = np.sqrt(2.0 / np.pi)
    u = c * (x + 0.044715 * x ** 3)
    tu = np.tanh(u)
    du = c * (1.0 + 3 * 0.044715 * x ** 2)

    return {
        "sigmoid": s,
        "d_sigmoid": s * (1.0 - s),
        "tanh": t,
        "d_tanh": 1.0 - t * t,
        "relu": np.where(pos, x, 0.0),
        "d_relu": pos.astype(float),
        "leaky_relu": np.where(pos, x, alpha * x),
        "d_leaky_relu": np.where(pos, 1.0, alpha),
        "gelu": 0.5 * x * (1.0 + tu),
        "d_gelu": 0.5 * (1.0 + tu) + 0.5 * x * (1.0 - tu * tu) * du,
    }
