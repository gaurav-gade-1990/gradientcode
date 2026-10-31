# Bug: shifts by the global max np.max(x) instead of each slice's own max, so a slice far below the
# global max underflows to all zeros and becomes 0 / 0 = nan.
import numpy as np


def softmax(x, axis=-1):
    e = np.exp(x - np.max(x))
    return e / np.sum(e, axis=axis, keepdims=True)
