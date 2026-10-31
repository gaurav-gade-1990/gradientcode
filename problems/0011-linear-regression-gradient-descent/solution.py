import numpy as np


def linear_regression_gd(X: np.ndarray, y: np.ndarray, lr: float, n_iters: int) -> tuple:
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_iters):
        r = X @ w + b - y
        dw = (2.0 / n) * (X.T @ r)
        db = (2.0 / n) * np.sum(r)
        w = w - lr * dw
        b = b - lr * db
    return w, float(b)
