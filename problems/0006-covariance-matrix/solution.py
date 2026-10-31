import numpy as np


def covariance(X: np.ndarray) -> np.ndarray:
    n = X.shape[0]
    Xc = X - X.mean(axis=0, keepdims=True)
    return Xc.T @ Xc / (n - 1)
