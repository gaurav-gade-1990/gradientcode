import numpy as np


def stratified_k_fold(y: np.ndarray, k: int) -> np.ndarray:
    y = np.asarray(y)
    folds = np.empty(len(y), dtype=np.int64)
    pos = 0
    for c in np.unique(y):  # ascending class order
        idx = np.flatnonzero(y == c)  # ascending sample order
        folds[idx] = (pos + np.arange(len(idx))) % k
        pos = (pos + len(idx)) % k
    return folds
