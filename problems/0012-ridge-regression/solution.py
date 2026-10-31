import numpy as np


def ridge_regression(X: np.ndarray, y: np.ndarray, alpha: float) -> tuple:
    x_mean = X.mean(axis=0)
    y_mean = y.mean()
    Xc = X - x_mean
    yc = y - y_mean
    d = X.shape[1]
    w = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(d), Xc.T @ yc)
    b = y_mean - x_mean @ w
    return w, float(b)
