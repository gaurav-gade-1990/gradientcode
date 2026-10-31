import numpy as np


def standardize(X_train, X_test):
    mu = X_train.mean(axis=0)
    sigma = X_train.std(axis=0) + 1e-12
    return (X_train - mu) / sigma, (X_test - mu) / sigma
