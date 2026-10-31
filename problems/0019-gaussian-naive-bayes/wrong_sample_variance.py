import numpy as np


def gaussian_nb(X_train, y_train, X_test, var_smoothing=1e-9):
    classes = np.unique(y_train)
    eps = var_smoothing * np.max(X_train.var(axis=0))
    priors = np.array([np.mean(y_train == c) for c in classes])
    mu = np.array([X_train[y_train == c].mean(axis=0) for c in classes])
    var = np.array([X_train[y_train == c].var(axis=0, ddof=1) for c in classes]) + eps
    diff = X_test[:, None, :] - mu[None]
    jll = np.log(priors) - 0.5 * np.sum(np.log(2 * np.pi * var)[None] + diff ** 2 / var[None], axis=2)
    mx = jll.max(axis=1, keepdims=True)
    lp = jll - mx - np.log(np.exp(jll - mx).sum(axis=1, keepdims=True))
    return classes[np.argmax(jll, axis=1)], lp
