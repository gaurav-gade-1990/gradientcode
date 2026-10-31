import numpy as np


def log_gaussian(X, means, variances):
    diff = X[:, None, :] - means[None, :, :]
    return -0.5 * np.sum(np.log(2 * np.pi * variances)[None] + diff ** 2 / variances[None], axis=2)


def gmm_em(X: np.ndarray, means: np.ndarray, variances: np.ndarray, weights: np.ndarray, n_iter: int, reg_covar: float = 1e-6) -> tuple:
    mu = np.array(means, dtype=float)
    var = np.array(variances, dtype=float)
    pi = np.array(weights, dtype=float)
    n = X.shape[0]
    history = []
    for _ in range(n_iter):
        log_r = np.log(pi)[None, :] + log_gaussian(X, mu, var)
        mx = log_r.max(axis=1, keepdims=True)
        L = mx + np.log(np.sum(np.exp(log_r - mx), axis=1, keepdims=True))
        history.append(float(np.sum(L)))
        r = np.exp(log_r - L)
        Nk = r.sum(axis=0)
        pi = Nk / n
        mu = (r.T @ X) / Nk[:, None]
        diff = X[:, None, :] - mu[None, :, :]
        var = np.einsum("ik,ikj->kj", r, diff ** 2) / Nk[:, None] + reg_covar
    return mu, var, pi, np.array(history)
