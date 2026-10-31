import numpy as np


def power_iteration(A: np.ndarray, v0: np.ndarray, n_iters: int) -> tuple:
    v = v0 / np.linalg.norm(v0)
    for _ in range(n_iters):
        w = A @ v
        v = w / np.linalg.norm(w)
    return float(v @ A @ v), v
