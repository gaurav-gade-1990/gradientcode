import numpy as np


def perceptron(X: np.ndarray, y: np.ndarray, n_epochs: int, lr: float = 1.0) -> tuple:
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_epochs):
        for i in range(n):
            if y[i] * (X[i] @ w + b) <= 0:
                w = w + lr * y[i] * X[i]
                b = b + lr * y[i]
    return w, float(b)
