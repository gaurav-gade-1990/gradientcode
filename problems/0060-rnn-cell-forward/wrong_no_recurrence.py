import numpy as np


def rnn_forward(x, h0, W_xh, W_hh, b):
    return np.tanh(x @ W_xh + (h0 @ W_hh)[:, None, :] + b)
