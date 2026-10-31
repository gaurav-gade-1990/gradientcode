import numpy as np


def confusion_matrix(y_true, y_pred, num_classes):
    C = int(max(y_true.max(), y_pred.max())) + 1 if len(y_true) else num_classes
    cm = np.zeros((C, C), dtype=np.int64)
    np.add.at(cm, (y_true, y_pred), 1)
    return cm
