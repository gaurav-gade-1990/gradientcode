import numpy as np


def logsumexp(x: np.ndarray, axis: int = -1) -> np.ndarray:
    c = np.max(x, axis=axis, keepdims=True)
    s = np.log(np.sum(np.exp(x - c), axis=axis, keepdims=True)) + c
    return np.squeeze(s, axis=axis)
