import numpy as np


def top_k(x, k):
    m = x.shape[1]
    idx = np.argpartition(x, m - k, axis=1)[:, m - k:]
    return np.take_along_axis(x, idx, axis=1), idx
