import numpy as np


def power_iteration(A, v0, n_iters):
    v = v0
    for _ in range(n_iters):
        w = A @ v
        v = w / np.linalg.norm(w)
    return float(v @ A @ v), v
