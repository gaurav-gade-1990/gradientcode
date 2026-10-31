import numpy as np


def sliding_windows(x, window, stride):
    n = len(x)
    if n < window:
        return np.zeros((0, window), dtype=x.dtype)
    num = (n - window + 1) // stride
    idx = np.arange(num)[:, None] * stride + np.arange(window)[None, :]
    return x[idx]
