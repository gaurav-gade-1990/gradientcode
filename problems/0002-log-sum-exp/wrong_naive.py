import numpy as np


def logsumexp(x, axis=-1):
    return np.log(np.sum(np.exp(x), axis=axis))
