import numpy as np


def log_loss(y_true, p, eps=1e-15):
    y = y_true.astype(float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
