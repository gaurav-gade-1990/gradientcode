import numpy as np


def gaussian_nb(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, var_smoothing: float = 1e-9) -> tuple:
    classes = np.unique(y_train)
    eps = var_smoothing * np.max(X_train.var(axis=0))
    priors = np.array([np.mean(y_train == c) for c in classes])
    mu = np.array([X_train[y_train == c].mean(axis=0) for c in classes])
    var = np.array([X_train[y_train == c].var(axis=0) for c in classes]) + eps
    diff = X_test[:, None, :] - mu[None, :, :]
    jll = np.log(priors)[None, :] - 0.5 * np.sum(np.log(2 * np.pi * var)[None] + diff ** 2 / var[None], axis=2)
    mx = jll.max(axis=1, keepdims=True)
    log_norm = mx + np.log(np.sum(np.exp(jll - mx), axis=1, keepdims=True))
    pred = classes[np.argmax(jll, axis=1)]
    return pred, jll - log_norm
