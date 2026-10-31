import numpy as np


def precision_recall_f1(y_true, y_pred, num_classes):
    acc = float(np.mean(y_true == y_pred))
    return acc, acc, acc
