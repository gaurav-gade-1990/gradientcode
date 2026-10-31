import numpy as np


def fit_linear_regression(X, y):
    w, *_ = np.linalg.lstsq(X, y, rcond=None)
    return w, 0.0
