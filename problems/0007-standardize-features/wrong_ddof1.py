import numpy as np


def standardize(X_train, X_test):
    mu = X_train.mean(axis=0)
    sigma = X_train.std(axis=0, ddof=1) if X_train.shape[0] > 1 else np.ones(X_train.shape[1])
    sigma = np.where(sigma == 0, 1.0, sigma)
    return (X_train - mu) / sigma, (X_test - mu) / sigma
