import numpy as np


def sliding_windows(x, window, stride):
    n = len(x)
    if n < window:
        return np.zeros((0, window), dtype=x.dtype)
    num = (n - window) // stride + 1
    return x[: num * window].reshape(num, window)
