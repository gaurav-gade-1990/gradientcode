import numpy as np


def log_loss(y_true, p, eps=1e-15):
    y = y_true.astype(float)
    q = np.clip(p, eps, 1 - eps)
    return float(-np.sum(y * np.log(q) + (1 - y) * np.log(1 - q)))
