import numpy as np


def sigmoid(a):
    return 1.0 / (1.0 + np.exp(-a))


def gru_forward(x, h0, W_ih, W_hh, b_ih, b_hh):
    B, T, _ = x.shape
    H = h0.shape[1]
    h = h0
    states = np.empty((B, T, H))
    for t in range(T):
        gi = x[:, t] @ W_ih + b_ih
        gh = h @ W_hh + b_hh
        r = sigmoid(gi[:, :H] + gh[:, :H])
        z = sigmoid(gi[:, H:2 * H] + gh[:, H:2 * H])
        n = np.tanh(gi[:, 2 * H:] + r * gh[:, 2 * H:])
        h = z * n + (1 - z) * h
        states[:, t] = h
    return states
