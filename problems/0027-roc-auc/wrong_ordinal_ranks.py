import numpy as np


def roc_auc(y_true, scores):
    y = y_true == 1
    ranks = np.argsort(np.argsort(scores, kind="stable"), kind="stable") + 1.0
    n_pos = y.sum()
    n_neg = len(y) - n_pos
    return float((ranks[y].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
