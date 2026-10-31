import numpy as np


def average_precision(y_true, scores):
    order = np.argsort(-scores, kind="stable")
    s = scores[order]
    y = (y_true[order] == 1).astype(float)
    last = np.flatnonzero(np.r_[s[1:] != s[:-1], True])
    tp = np.cumsum(y)[last]
    precision = tp / (last + 1.0)
    precision = np.maximum.accumulate(precision[::-1])[::-1]
    recall = tp / y.sum()
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))
