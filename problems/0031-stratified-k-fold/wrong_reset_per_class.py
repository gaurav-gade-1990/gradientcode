import numpy as np


def stratified_k_fold(y, k):
    folds = np.empty(len(y), dtype=np.int64)
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        folds[idx] = np.arange(len(idx)) % k
    return folds
