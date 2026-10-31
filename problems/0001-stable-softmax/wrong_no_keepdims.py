import numpy as np


def softmax(x, axis=-1):
    z = x - np.max(x)
    e = np.exp(z)
    return e / np.sum(e, axis=axis)
