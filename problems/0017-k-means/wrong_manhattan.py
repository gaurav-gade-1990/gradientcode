import numpy as np


def kmeans(X, init_centroids, max_iter):
    C = np.array(init_centroids, dtype=float)
    k = C.shape[0]
    for _ in range(max_iter):
        labels = np.argmin(np.abs(X[:, None, :] - C[None]).sum(-1), axis=1)
        new = C.copy()
        for j in range(k):
            if np.any(labels == j):
                new[j] = X[labels == j].mean(axis=0)
        if np.array_equal(new, C):
            break
        C = new
    return C, np.argmin(np.abs(X[:, None, :] - C[None]).sum(-1), axis=1)
