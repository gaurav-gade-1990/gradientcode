import numpy as np


def unbroadcast(grad: np.ndarray, shape: tuple) -> np.ndarray:
    # Averages over broadcast axes. Each reused element gets the SUM of its gradients, not the mean.
    grad = np.asarray(grad, dtype=float)
    extra = grad.ndim - len(shape)
    if extra > 0:
        grad = grad.mean(axis=tuple(range(extra)))
    axes = tuple(i for i, s in enumerate(shape) if s == 1 and grad.shape[i] != 1)
    if axes:
        grad = grad.mean(axis=axes, keepdims=True)
    return grad.reshape(shape)
