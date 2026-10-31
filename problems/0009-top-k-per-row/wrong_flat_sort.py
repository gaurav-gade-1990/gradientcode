import numpy as np


def top_k(x, k):
    idx = np.argsort(-x, axis=0, kind="stable")[:k].T
    vals = np.take_along_axis(x, idx, axis=1)
    return vals, idx
