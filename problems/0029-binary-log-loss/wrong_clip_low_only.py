import numpy as np


def log_loss(y_true, p, eps=1e-15):
    y = y_true.astype(float)
    q = np.maximum(p, eps)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q + eps)))
