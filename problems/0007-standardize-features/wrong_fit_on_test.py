import numpy as np


def _z(X):
    s = X.std(axis=0)
    return (X - X.mean(axis=0)) / np.where(s == 0, 1.0, s)


def standardize(X_train, X_test):
    return _z(X_train), _z(X_test)
