import numpy as np


def rmsnorm(x, weight, eps=1e-6):
    rms = np.sqrt(np.mean(x * x) + eps)
    return x / rms * weight
