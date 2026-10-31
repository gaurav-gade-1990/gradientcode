import numpy as np


def pairwise_distances(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    aa = np.sum(A * A, axis=1)[:, None]
    bb = np.sum(B * B, axis=1)[None, :]
    d2 = aa - 2.0 * (A @ B.T) + bb
    return np.sqrt(np.maximum(d2, 0.0))
