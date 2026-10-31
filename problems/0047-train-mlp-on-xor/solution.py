import numpy as np


def _forward(X, W1, b1, W2, b2):
    h = np.tanh(X @ W1 + b1)            # (N, H)
    z = (h @ W2 + b2)[:, 0]             # (N,)
    return h, z


def train_mlp(X, y, W1, b1, W2, b2, lr, epochs):
    W1, b1, W2, b2 = W1.copy(), b1.copy(), W2.copy(), b2.copy()
    N = X.shape[0]
    losses = np.empty(epochs)
    for t in range(epochs):
        h, z = _forward(X, W1, b1, W2, b2)
        # BCE from logits, stable: log(1 + e^z) - y z
        losses[t] = np.mean(np.logaddexp(0.0, z) - y * z)
        p = 1.0 / (1.0 + np.exp(-z))

        dz = ((p - y) / N)[:, None]     # (N, 1)
        dW2 = h.T @ dz
        db2 = dz.sum(axis=0)
        dh = dz @ W2.T                  # uses W2 before its update
        da = dh * (1.0 - h * h)
        dW1 = X.T @ da
        db1 = da.sum(axis=0)

        W1 -= lr * dW1
        b1 -= lr * db1
        W2 -= lr * dW2
        b2 -= lr * db2
    _, z = _forward(X, W1, b1, W2, b2)
    return losses, 1.0 / (1.0 + np.exp(-z))
