import numpy as np


def confusion_matrix(y_true, y_pred, num_classes):
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    cm[y_true, y_pred] += 1
    return cm
