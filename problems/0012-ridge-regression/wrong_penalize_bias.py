import numpy as np


def ridge_regression(X, y, alpha):
    A = np.hstack([X, np.ones((X.shape[0], 1))])
    theta = np.linalg.solve(A.T @ A + alpha * np.eye(A.shape[1]), A.T @ y)
    return theta[:-1], float(theta[-1])
