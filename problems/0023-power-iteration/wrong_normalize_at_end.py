import numpy as np


def power_iteration(A, v0, n_iters):
    v = v0 / np.linalg.norm(v0)
    for _ in range(n_iters):
        v = A @ v
    v = v / np.linalg.norm(v)
    return float(v @ A @ v), v
