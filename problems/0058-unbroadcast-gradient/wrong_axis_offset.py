import numpy as np


def unbroadcast(grad: np.ndarray, shape: tuple) -> np.ndarray:
    # Sums the size-1 axes BEFORE dropping leading axes, using the target's axis numbers
    # on grad without shifting them. Right only when no leading axes were added.
    grad = np.asarray(grad, dtype=float)
    for i, s in enumerate(shape):
        if s == 1 and i < grad.ndim:
            grad = grad.sum(axis=i, keepdims=True)
    while grad.ndim > len(shape):
        grad = grad.sum(axis=0)
    return grad.reshape(shape)
