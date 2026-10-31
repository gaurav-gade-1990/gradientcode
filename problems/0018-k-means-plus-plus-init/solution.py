import numpy as np


def kmeans_pp_init(X: np.ndarray, k: int, u: np.ndarray) -> np.ndarray:
    n = X.shape[0]
    idx = [min(int(np.floor(u[0] * n)), n - 1)]
    D2 = np.sum((X - X[idx[0]]) ** 2, axis=1)
    for j in range(1, k):
        cum = np.cumsum(D2)
        c = int(np.searchsorted(cum, u[j] * cum[-1], side="right"))
        idx.append(c)
        D2 = np.minimum(D2, np.sum((X - X[c]) ** 2, axis=1))
    return np.array(idx, dtype=np.int64)
