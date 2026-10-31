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
    nonneg = x >= 0
    return {
        "sigmoid": s, "d_sigmoid": s * (1 - s),
        "tanh": t, "d_tanh": 1 - t * t,
        "relu": np.maximum(x, 0.0), "d_relu": nonneg.astype(float),
        "leaky_relu": np.where(nonneg, x, alpha * x), "d_leaky_relu": np.where(nonneg, 1.0, alpha),
        "gelu": 0.5 * x * (1 + tu), "d_gelu": 0.5 * (1 + tu) + 0.5 * x * (1 - tu * tu) * du,
    }
