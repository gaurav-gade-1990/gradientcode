import numpy as np


def _loss(X, y, W1, b1, W2, b2):
    h = np.tanh(X @ W1 + b1)
    p = 1 / (1 + np.exp(-(h @ W2 + b2)[:, 0]))
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))


def train_mlp(X, y, W1, b1, W2, b2, lr, epochs):
    W1, b1, W2, b2 = W1.copy(), b1.copy(), W2.copy(), b2.copy()
    N = X.shape[0]
    losses = np.empty(epochs)
    for t in range(epochs):
        h = np.tanh(X @ W1 + b1)
        p = 1 / (1 + np.exp(-(h @ W2 + b2)[:, 0]))
        dz = ((p - y) / N)[:, None]
        dW2, db2 = h.T @ dz, dz.sum(axis=0)
        da = (dz @ W2.T) * (1 - h * h)
        dW1, db1 = X.T @ da, da.sum(axis=0)
        W1 -= lr * dW1; b1 -= lr * db1; W2 -= lr * dW2; b2 -= lr * db2
        losses[t] = _loss(X, y, W1, b1, W2, b2)   # recorded after the update
    h = np.tanh(X @ W1 + b1)
    return losses, 1 / (1 + np.exp(-(h @ W2 + b2)[:, 0]))
