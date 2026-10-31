import numpy as np


def _safe_div(a, b):
    return np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b != 0)


def precision_recall_f1(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> tuple:
    C = num_classes
    cm = np.bincount(y_true * C + y_pred, minlength=C * C).reshape(C, C).astype(float)
    tp = np.diag(cm)
    fp = cm.sum(axis=0) - tp
    fn = cm.sum(axis=1) - tp
    p = _safe_div(tp, tp + fp)
    r = _safe_div(tp, tp + fn)
    f = _safe_div(2 * p * r, p + r)
    return float(p.mean()), float(r.mean()), float(f.mean())
