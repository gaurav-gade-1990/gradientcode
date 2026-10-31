import numpy as np


def fit_linear_regression(X: np.ndarray, y: np.ndarray) -> tuple:
    A = np.hstack([X, np.ones((X.shape[0], 1))])
    theta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return theta[:-1], float(theta[-1])
