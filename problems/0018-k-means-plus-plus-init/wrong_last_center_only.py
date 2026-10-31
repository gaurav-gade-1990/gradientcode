import numpy as np


def kmeans_pp_init(X, k, u):
    n = X.shape[0]
    idx = [int(u[0] * n)]
    for j in range(1, k):
        D2 = np.sum((X - X[idx[-1]]) ** 2, axis=1)
        cum = np.cumsum(D2)
        c = int(np.searchsorted(cum, u[j] * cum[-1], side="right"))
        idx.append(c)
    return np.array(idx, dtype=np.int64)
