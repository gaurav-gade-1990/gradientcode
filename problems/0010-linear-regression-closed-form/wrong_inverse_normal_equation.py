import numpy as np


def fit_linear_regression(X, y):
    A = np.hstack([X, np.ones((X.shape[0], 1))])
    theta = np.linalg.inv(A.T @ A) @ A.T @ y
    return theta[:-1], float(theta[-1])
