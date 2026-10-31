import numpy as np


def kmeans_pp_init(X, k, u):
    n = X.shape[0]
    idx = [int(u[0] * n)]
    D2 = np.sum((X - X[idx[0]]) ** 2, axis=1)
    for j in range(1, k):
        cum = np.cumsum(D2)
        c = int(np.searchsorted(cum, u[j] * cum[-1]))
        idx.append(c)
        D2 = np.minimum(D2, np.sum((X - X[c]) ** 2, axis=1))
    return np.array(idx, dtype=np.int64)
