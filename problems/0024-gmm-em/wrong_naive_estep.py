import numpy as np


def gmm_em(X, means, variances, weights, n_iter, reg_covar=1e-6):
    mu, var, pi = np.array(means, float), np.array(variances, float), np.array(weights, float)
    n = X.shape[0]
    hist = []
    for _ in range(n_iter):
        diff = X[:, None, :] - mu[None]
        dens = np.exp(-0.5 * np.sum(diff ** 2 / var[None], axis=2)) / np.sqrt(np.prod(2 * np.pi * var, axis=1))[None]
        p = pi[None] * dens
        tot = p.sum(axis=1, keepdims=True)
        hist.append(float(np.sum(np.log(tot))))
        r = p / tot
        Nk = r.sum(0)
        pi = Nk / n
        mu = r.T @ X / Nk[:, None]
        diff = X[:, None, :] - mu[None]
        var = np.einsum("ik,ikj->kj", r, diff ** 2) / Nk[:, None] + reg_covar
    return mu, var, pi, np.array(hist)
