import numpy as np


def average_precision(y_true, scores):
    order = np.argsort(-scores, kind="stable")
    y = (y_true[order] == 1).astype(float)
    tp = np.cumsum(y)
    precision = tp / np.arange(1, len(y) + 1)
    return float(np.sum(precision * y) / y.sum())
