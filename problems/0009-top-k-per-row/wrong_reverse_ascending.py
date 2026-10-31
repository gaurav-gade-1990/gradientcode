import numpy as np


def top_k(x, k):
    idx = np.argsort(x, axis=1, kind="stable")[:, ::-1][:, :k]
    return np.take_along_axis(x, idx, axis=1), idx
