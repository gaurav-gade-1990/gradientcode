import numpy as np


def sliding_windows(x: np.ndarray, window: int, stride: int) -> np.ndarray:
    n = x.shape[0]
    if n < window:
        return np.zeros((0, window), dtype=x.dtype)
    num = (n - window) // stride + 1
    idx = np.arange(num)[:, None] * stride + np.arange(window)[None, :]
    return x[idx]
