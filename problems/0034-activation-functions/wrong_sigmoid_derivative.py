import numpy as np


def activations(x, alpha=0.01):
    x = np.asarray(x, dtype=float)
    e = np.exp(-np.abs(x))
    s = np.where(x >= 0, 1.0 / (1.0 + e), e / (1.0 + e))
    t = np.tanh(x)
    c = np.sqrt(2.0 / np.pi)
    u = c * (x + 0.044715 * x ** 3)
    tu = np.tanh(u)
    du = c * (1.0 + 3 * 0.044715 * x ** 2)
    pos = x > 0
    return {
        # Applies the derivative formula to x instead of to sigmoid(x).
        "sigmoid": s, "d_sigmoid": x * (1 - x),
        "tanh": t, "d_tanh": 1 - t * t,
        "relu": np.where(pos, x, 0.0), "d_relu": pos.astype(float),
        "leaky_relu": np.where(pos, x, alpha * x), "d_leaky_relu": np.where(pos, 1.0, alpha),
        "gelu": 0.5 * x * (1 + tu), "d_gelu": 0.5 * (1 + tu) + 0.5 * x * (1 - tu * tu) * du,
    }
