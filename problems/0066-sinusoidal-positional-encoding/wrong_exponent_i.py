import numpy as np


def positional_encoding(max_len, d_model, base=10000.0):
    pos = np.arange(max_len)[:, None]
    freq = base ** (-np.arange(d_model // 2) / d_model)
    angles = pos * freq[None, :]
    pe = np.empty((max_len, d_model))
    pe[:, 0::2] = np.sin(angles)
    pe[:, 1::2] = np.cos(angles)
    return pe
