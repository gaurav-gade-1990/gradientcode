import numpy as np


def logistic_regression_gd(X, y, lr, n_iters):
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_iters):
        z = X @ w + b
        p = np.exp(z) / (1.0 + np.exp(z))
        g = p - y
        w = w - lr * X.T @ g / n
        b = b - lr * np.mean(g)
    return w, float(b)
