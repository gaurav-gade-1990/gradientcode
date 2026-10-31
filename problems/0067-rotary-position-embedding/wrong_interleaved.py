import numpy as np


def apply_rope(x, positions, base=10000.0):
    d = x.shape[-1]
    half = d // 2
    theta = base ** (-np.arange(half) * 2.0 / d)
    phi = np.asarray(positions, dtype=float)[:, None] * theta[None, :]
    cos, sin = np.cos(phi), np.sin(phi)
    x1, x2 = x[..., 0::2], x[..., 1::2]
    out = np.empty_like(x)
    out[..., 0::2] = x1 * cos - x2 * sin
    out[..., 1::2] = x2 * cos + x1 * sin
    return out
