import numpy as np


def dropout(x, keep_prob, u, train=True):
    if not train:
        return np.array(x, dtype=float)
    return x * (u <= keep_prob) / keep_prob
