import numpy as np


def linear_svm(X: np.ndarray, y: np.ndarray, lam: float, n_iters: int) -> tuple:
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for t in range(1, n_iters + 1):
        margins = y * (X @ w + b)
        active = margins < 1
        ya = y * active
        g_w = lam * w - (ya @ X) / n
        g_b = -np.sum(ya) / n
        eta = 1.0 / (lam * t)
        w = w - eta * g_w
        b = b - eta * g_b
    return w, float(b)
