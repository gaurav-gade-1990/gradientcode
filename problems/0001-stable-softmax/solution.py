import numpy as np


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    z = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(z)
    return e / np.sum(e, axis=axis, keepdims=True)
