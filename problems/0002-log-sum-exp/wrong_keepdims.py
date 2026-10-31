import numpy as np


def logsumexp(x, axis=-1):
    c = np.max(x, axis=axis, keepdims=True)
    return np.log(np.sum(np.exp(x - c), axis=axis, keepdims=True)) + c
