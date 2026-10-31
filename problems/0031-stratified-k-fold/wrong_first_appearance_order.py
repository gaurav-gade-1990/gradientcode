import numpy as np


def stratified_k_fold(y, k):
    folds = np.empty(len(y), dtype=np.int64)
    pos = 0
    _, first = np.unique(y, return_index=True)
    for c in y[np.sort(first)]:
        idx = np.flatnonzero(y == c)
        folds[idx] = (pos + np.arange(len(idx))) % k
        pos = (pos + len(idx)) % k
    return folds
