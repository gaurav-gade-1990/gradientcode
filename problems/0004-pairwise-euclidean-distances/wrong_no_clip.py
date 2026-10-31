import numpy as np


def pairwise_distances(A, B):
    aa = np.sum(A * A, axis=1)[:, None]
    bb = np.sum(B * B, axis=1)[None, :]
    return np.sqrt(aa - 2.0 * (A @ B.T) + bb)
