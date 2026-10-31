import numpy as np


def average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores, kind="stable")
    s = scores[order]
    y = (np.asarray(y_true)[order] == 1).astype(float)
    # last index of each group of tied scores = one threshold
    last = np.flatnonzero(np.r_[s[1:] != s[:-1], True])
    tp = np.cumsum(y)[last]
    k = last + 1.0
    precision = tp / k
    recall = tp / y.sum()
    d_recall = np.diff(np.r_[0.0, recall])
    return float(np.sum(d_recall * precision))
