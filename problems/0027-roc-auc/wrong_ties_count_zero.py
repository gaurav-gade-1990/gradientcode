import numpy as np


def roc_auc(y_true, scores):
    pos = scores[y_true == 1]
    neg = scores[y_true == 0]
    return float(np.mean(pos[:, None] > neg[None, :]))
