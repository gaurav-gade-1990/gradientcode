# Bug: treats any std below 1e-8 as constant, but the statement replaces sigma only when it is exactly 0,
# so a column with a tiny but real spread is only centered instead of scaled.
import numpy as np


def standardize(X_train, X_test):
    mu = X_train.mean(axis=0)
    sigma = X_train.std(axis=0)
    sigma = np.where(sigma < 1e-8, 1.0, sigma)
    return (X_train - mu) / sigma, (X_test - mu) / sigma
