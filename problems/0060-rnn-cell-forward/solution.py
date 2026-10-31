import numpy as np


def rnn_forward(x, h0, W_xh, W_hh, b):
    B, T, _ = x.shape
    h = h0
    states = np.empty((B, T, h0.shape[1]))
    for t in range(T):
        h = np.tanh(x[:, t] @ W_xh + h @ W_hh + b)
        states[:, t] = h
    return states
