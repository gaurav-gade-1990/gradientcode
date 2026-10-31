import numpy as np


def covariance(X):
    Xc = X - X.mean(axis=0, keepdims=True)
    return Xc.T @ Xc / X.shape[0]
