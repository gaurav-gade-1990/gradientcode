# Bug: fixes the sign by making the first entry of each component positive, instead of the entry with
# the largest absolute value.
import numpy as np


def pca(X, k):
    Xc = X - X.mean(axis=0)
    cov = Xc.T @ Xc / (X.shape[0] - 1)
    vals, vecs = np.linalg.eigh(cov)
    vals, vecs = vals[::-1], vecs[:, ::-1]
    comps = vecs[:, :k].T.copy()
    comps *= np.where(comps[:, 0] < 0, -1.0, 1.0)[:, None]
    return Xc @ comps.T, comps, vals[:k] / vals.sum()
