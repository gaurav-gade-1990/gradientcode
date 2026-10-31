# Bug: takes the mean of every cluster, even an empty one, so an empty cluster's centroid becomes
# nan (the mean of zero points) instead of keeping its current value.
import numpy as np


def kmeans(X, init_centroids, max_iter):
    C = np.array(init_centroids, dtype=float)
    k = C.shape[0]
    for _ in range(max_iter):
        labels = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(-1), axis=1)
        new = np.array([X[labels == j].mean(axis=0) for j in range(k)])
        if np.array_equal(new, C):
            break
        C = new
    labels = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(-1), axis=1)
    return C, labels
