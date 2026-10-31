import numpy as np


def rmsnorm(x, weight, eps=1e-6):
    x = x - np.mean(x, axis=-1, keepdims=True)
    rms = np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + eps)
    return x / rms * weight
