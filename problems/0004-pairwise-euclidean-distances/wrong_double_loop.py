import numpy as np


def pairwise_distances(A, B):
    n, m = A.shape[0], B.shape[0]
    D = np.zeros((n, m))
    for i in range(n):
        for j in range(m):
            D[i, j] = np.sqrt(np.sum((A[i] - B[j]) ** 2))
    return D
