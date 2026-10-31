import numpy as np


def sigmoid(z):
    e = np.exp(-np.abs(z))
    return np.where(z >= 0, 1.0 / (1.0 + e), e / (1.0 + e))


def logistic_regression_gd(X: np.ndarray, y: np.ndarray, lr: float, n_iters: int) -> tuple:
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_iters):
        p = sigmoid(X @ w + b)
        g = p - y
        dw = X.T @ g / n
        db = np.mean(g)
        w = w - lr * dw
        b = b - lr * db
    return w, float(b)
