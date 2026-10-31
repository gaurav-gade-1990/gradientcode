# Bug: the active test is margins <= 1 instead of the strict margins < 1, so a sample sitting exactly
# on the margin still pulls on w and b.
import numpy as np


def linear_svm(X, y, lam, n_iters):
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for t in range(1, n_iters + 1):
        active = y * (X @ w + b) <= 1
        ya = y * active
        g_w = lam * w - (ya @ X) / n
        g_b = -np.sum(ya) / n
        eta = 1.0 / (lam * t)
        w = w - eta * g_w
        b = b - eta * g_b
    return w, float(b)
