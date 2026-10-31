import numpy as np


def ridge_regression(X, y, alpha):
    Xc = X - X.mean(axis=0)
    yc = y - y.mean()
    w = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(X.shape[1]), Xc.T @ yc)
    return w, float(y.mean())
