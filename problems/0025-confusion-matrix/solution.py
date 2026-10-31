import numpy as np


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    C = num_classes
    flat = np.asarray(y_true, dtype=np.int64) * C + np.asarray(y_pred, dtype=np.int64)
    return np.bincount(flat, minlength=C * C).reshape(C, C).astype(np.int64)
