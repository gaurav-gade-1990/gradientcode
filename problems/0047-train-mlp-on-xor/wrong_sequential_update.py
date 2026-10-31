import numpy as np


def train_mlp(X, y, W1, b1, W2, b2, lr, epochs):
    W1, b1, W2, b2 = W1.copy(), b1.copy(), W2.copy(), b2.copy()
    N = X.shape[0]
    losses = np.empty(epochs)
    for t in range(epochs):
        h = np.tanh(X @ W1 + b1)
        z = (h @ W2 + b2)[:, 0]
        p = 1 / (1 + np.exp(-z))
        losses[t] = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        dz = ((p - y) / N)[:, None]
        # Updates the output layer first, then backprops through the NEW W2.
        W2 -= lr * (h.T @ dz)
        b2 -= lr * dz.sum(axis=0)
        da = (dz @ W2.T) * (1 - h * h)
        W1 -= lr * (X.T @ da)
        b1 -= lr * da.sum(axis=0)
    h = np.tanh(X @ W1 + b1)
    return losses, 1 / (1 + np.exp(-(h @ W2 + b2)[:, 0]))
