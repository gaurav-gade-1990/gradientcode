import numpy as np


def perceptron(X, y, n_epochs, lr=1.0):
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_epochs):
        mis = y * (X @ w + b) <= 0
        w = w + lr * (y[mis] @ X[mis])
        b = b + lr * np.sum(y[mis])
    return w, float(b)
