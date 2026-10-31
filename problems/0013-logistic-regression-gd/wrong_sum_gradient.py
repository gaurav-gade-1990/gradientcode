import numpy as np


def logistic_regression_gd(X, y, lr, n_iters):
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_iters):
        z = X @ w + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))
        g = p - y
        w = w - lr * X.T @ g
        b = b - lr * np.sum(g)
    return w, float(b)
