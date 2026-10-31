# Bug: np.squeeze(s) without axis removes every size-1 axis, not just the reduced one, so a (1, 3)
# input reduced over axis 1 comes back with shape () instead of (1,).
import numpy as np


def logsumexp(x, axis=-1):
    c = np.max(x, axis=axis, keepdims=True)
    s = np.log(np.sum(np.exp(x - c), axis=axis, keepdims=True)) + c
    return np.squeeze(s)
