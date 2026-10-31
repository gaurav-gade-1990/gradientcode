import numpy as np


def kmeans_pp_init(X, k, u):
    n = X.shape[0]
    idx = [int(u[0] * n)]
    D = np.sqrt(np.sum((X - X[idx[0]]) ** 2, axis=1))
    for j in range(1, k):
        cum = np.cumsum(D)
        c = int(np.searchsorted(cum, u[j] * cum[-1], side="right"))
        idx.append(c)
        D = np.minimum(D, np.sqrt(np.sum((X - X[c]) ** 2, axis=1)))
    return np.array(idx, dtype=np.int64)
