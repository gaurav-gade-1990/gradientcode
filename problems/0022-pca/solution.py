import numpy as np


def pca(X: np.ndarray, k: int) -> tuple:
    Xc = X - X.mean(axis=0)
    cov = Xc.T @ Xc / (X.shape[0] - 1)
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    comps = vecs[:, :k].T.copy()
    pivot = np.argmax(np.abs(comps), axis=1)
    signs = np.sign(comps[np.arange(k), pivot])
    comps *= signs[:, None]
    Z = Xc @ comps.T
    ratio = vals[:k] / np.sum(vals)
    return Z, comps, ratio
