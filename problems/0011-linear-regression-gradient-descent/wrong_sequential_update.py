import numpy as np


def linear_regression_gd(X, y, lr, n_iters):
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_iters):
        r = X @ w + b - y
        w = w - lr * (2.0 / n) * (X.T @ r)
        r = X @ w + b - y
        b = b - lr * (2.0 / n) * np.sum(r)
    return w, float(b)
