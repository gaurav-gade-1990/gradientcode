import numpy as np


def pca(X, k):
    Xc = X - X.mean(axis=0)
    cov = Xc.T @ Xc / (X.shape[0] - 1)
    vals, vecs = np.linalg.eigh(cov)
    vals, vecs = vals[::-1], vecs[:, ::-1]
    comps = vecs[:, :k].T
    return Xc @ comps.T, comps, vals[:k] / vals.sum()
