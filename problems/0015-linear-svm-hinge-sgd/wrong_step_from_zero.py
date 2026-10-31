import numpy as np


def linear_svm(X, y, lam, n_iters):
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for t in range(n_iters):
        active = y * (X @ w + b) < 1
        ya = y * active
        g_w = lam * w - (ya @ X) / n
        g_b = -np.sum(ya) / n
        eta = 1.0 / (lam * (t + 2))
        w = w - eta * g_w
        b = b - eta * g_b
    return w, float(b)
