import numpy as np


def _safe_div(a, b):
    return np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b != 0)


def precision_recall_f1(y_true, y_pred, num_classes):
    C = num_classes
    cm = np.bincount(y_true * C + y_pred, minlength=C * C).reshape(C, C).astype(float)
    tp = np.diag(cm)
    p = _safe_div(tp, cm.sum(axis=0)).mean()
    r = _safe_div(tp, cm.sum(axis=1)).mean()
    f = 2 * p * r / (p + r) if p + r > 0 else 0.0
    return float(p), float(r), float(f)
