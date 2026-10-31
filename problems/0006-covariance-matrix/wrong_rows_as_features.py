import numpy as np


def covariance(X):
    Xc = X - X.mean(axis=1, keepdims=True)
    return Xc @ Xc.T / (X.shape[1] - 1)
