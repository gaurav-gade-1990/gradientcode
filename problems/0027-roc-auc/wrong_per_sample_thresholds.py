import numpy as np


def roc_auc(y_true, scores):
    order = np.argsort(-scores, kind="stable")
    y = y_true[order]
    tpr = np.r_[0.0, np.cumsum(y == 1) / np.sum(y == 1)]
    fpr = np.r_[0.0, np.cumsum(y == 0) / np.sum(y == 0)]
    return float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2))
