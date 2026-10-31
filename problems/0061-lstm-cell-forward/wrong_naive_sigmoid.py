import numpy as np


def sigmoid(a):
    return np.exp(a) / (1.0 + np.exp(a))


def lstm_cell(x, h_prev, c_prev, W, U, b):
    H = h_prev.shape[1]
    z = x @ W + h_prev @ U + b
    i = sigmoid(z[:, 0:H])
    f = sigmoid(z[:, H:2 * H])
    g = np.tanh(z[:, 2 * H:3 * H])
    o = sigmoid(z[:, 3 * H:4 * H])
    c = f * c_prev + i * g
    h = o * np.tanh(c)
    return h, c
