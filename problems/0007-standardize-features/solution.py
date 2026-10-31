import numpy as np


def standardize(X_train: np.ndarray, X_test: np.ndarray) -> tuple:
    mu = X_train.mean(axis=0)
    sigma = X_train.std(axis=0)
    sigma = np.where(sigma == 0, 1.0, sigma)
    return (X_train - mu) / sigma, (X_test - mu) / sigma
