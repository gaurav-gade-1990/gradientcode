import numpy as np


def apply_rope(x, positions, base=10000.0):
    d = x.shape[-1]
    half = d // 2
    theta = base ** (-np.arange(half) * 1.0 / d)
    phi = np.asarray(positions, dtype=float)[:, None] * theta[None, :]
    cos, sin = np.cos(phi), np.sin(phi)
    x1, x2 = x[..., :half], x[..., half:]
    return np.concatenate([x1 * cos - x2 * sin, x2 * cos + x1 * sin], axis=-1)
