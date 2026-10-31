import numpy as np


def sigmoid(a):
    e = np.exp(-np.abs(a))
    return np.where(a >= 0, 1.0 / (1.0 + e), e / (1.0 + e))


def lstm_cell(x, h_prev, c_prev, W, U, b):
    H = h_prev.shape[1]
    z = (x @ W + h_prev @ U + b).reshape(-1, H, 4)
    z = np.concatenate([z[:, :, k] for k in range(4)], axis=1)
    i = sigmoid(z[:, 0:H])
    f = sigmoid(z[:, H:2 * H])
    g = np.tanh(z[:, 2 * H:3 * H])
    o = sigmoid(z[:, 3 * H:4 * H])
    c = f * c_prev + i * g
    h = o * np.tanh(c)
    return h, c
