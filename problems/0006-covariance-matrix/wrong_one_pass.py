# Bug: the one-pass formula X^T X - n * mean mean^T (then / (n - 1)) subtracts two huge, nearly equal
# numbers, so it loses every significant digit when the means are large relative to the spread.
import numpy as np


def covariance(X):
    n = X.shape[0]
    m = X.mean(axis=0)
    return (X.T @ X - n * np.outer(m, m)) / (n - 1)
