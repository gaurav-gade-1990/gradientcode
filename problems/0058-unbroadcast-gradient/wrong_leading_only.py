import numpy as np


def unbroadcast(grad: np.ndarray, shape: tuple) -> np.ndarray:
    # Sums the extra leading axes but forgets size-1 axes that were stretched.
    grad = np.asarray(grad, dtype=float)
    while grad.ndim > len(shape):
        grad = grad.sum(axis=0)
    return grad
