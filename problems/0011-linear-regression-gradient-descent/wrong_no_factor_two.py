import numpy as np


def linear_regression_gd(X, y, lr, n_iters):
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_iters):
        r = X @ w + b - y
        w = w - lr * (X.T @ r) / n
        b = b - lr * np.sum(r) / n
    return w, float(b)
