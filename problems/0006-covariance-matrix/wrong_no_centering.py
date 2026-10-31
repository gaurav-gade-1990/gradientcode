import numpy as np


def covariance(X):
    return X.T @ X / (X.shape[0] - 1)
