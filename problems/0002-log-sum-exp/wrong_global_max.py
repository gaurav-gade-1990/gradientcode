import numpy as np


def logsumexp(x, axis=-1):
    c = np.max(x)
    return np.log(np.sum(np.exp(x - c), axis=axis)) + c
