import numpy as np


def assign(X, C):
    diff = X[:, None, :] - C[None, :, :]
    return np.argmin(np.sum(diff * diff, axis=-1), axis=1)


def kmeans(X: np.ndarray, init_centroids: np.ndarray, max_iter: int) -> tuple:
    C = np.array(init_centroids, dtype=float)
    k = C.shape[0]
    for _ in range(max_iter):
        labels = assign(X, C)
        new = C.copy()
        for j in range(k):
            members = X[labels == j]
            if len(members) > 0:
                new[j] = members.mean(axis=0)
        if np.array_equal(new, C):
            break
        C = new
    return C, assign(X, C)
