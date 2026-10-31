import numpy as np


def top_k(x: np.ndarray, k: int) -> tuple:
    idx = np.argsort(-x, axis=1, kind="stable")[:, :k]
    vals = np.take_along_axis(x, idx, axis=1)
    return vals, idx
