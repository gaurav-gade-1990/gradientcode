import numpy as np


def gmm_em(X, means, variances, weights, n_iter, reg_covar=1e-6):
    mu, var, pi = np.array(means, float), np.array(variances, float), np.array(weights, float)
    n = X.shape[0]
    hist = []
    for _ in range(n_iter):
        diff = X[:, None, :] - mu[None]
        log_r = np.log(pi)[None] - 0.5 * np.sum(np.log(2 * np.pi * var)[None] + diff ** 2 / var[None], axis=2)
        mx = log_r.max(1, keepdims=True)
        L = mx + np.log(np.exp(log_r - mx).sum(1, keepdims=True))
        hist.append(float(L.sum()))
        r = np.exp(log_r - L)
        Nk = r.sum(0)
        pi = Nk / n
        mu = r.T @ X / Nk[:, None]
        diff = X[:, None, :] - mu[None]
        var = np.einsum("ik,ikj->kj", r, diff ** 2) / Nk[:, None]
    return mu, var, pi, np.array(hist)
