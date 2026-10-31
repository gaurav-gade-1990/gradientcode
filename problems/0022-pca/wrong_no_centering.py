import numpy as np


def pca(X, k):
    cov = X.T @ X / (X.shape[0] - 1)
    vals, vecs = np.linalg.eigh(cov)
    vals, vecs = vals[::-1], vecs[:, ::-1]
    comps = vecs[:, :k].T.copy()
    pivot = np.argmax(np.abs(comps), axis=1)
    comps *= np.sign(comps[np.arange(k), pivot])[:, None]
    return X @ comps.T, comps, vals[:k] / vals.sum()
