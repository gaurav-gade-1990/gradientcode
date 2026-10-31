import numpy as np


def pca(X, k):
    Xc = X - X.mean(axis=0)
    cov = Xc.T @ Xc / (X.shape[0] - 1)
    vals, vecs = np.linalg.eigh(cov)
    comps = vecs[:, :k].T.copy()
    pivot = np.argmax(np.abs(comps), axis=1)
    comps *= np.sign(comps[np.arange(k), pivot])[:, None]
    return Xc @ comps.T, comps, vals[:k] / vals.sum()
