import numpy as np


def perceptron(X, y, n_epochs, lr=1.0):
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_epochs):
        for i in range(n):
            if y[i] * (X[i] @ w + b) < 0:
                w = w + lr * y[i] * X[i]
                b = b + lr * y[i]
    return w, float(b)
