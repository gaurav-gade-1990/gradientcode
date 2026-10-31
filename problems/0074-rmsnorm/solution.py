import numpy as np


def rmsnorm(x: np.ndarray, weight: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    rms = np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + eps)
    return x / rms * weight
