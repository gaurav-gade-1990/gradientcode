import numpy as np


def positional_encoding(max_len, d_model, base=10000.0):
    pos = np.arange(max_len)[:, None]
    freq = base ** (-np.arange(0, d_model, 2) / d_model)
    angles = pos * freq[None, :]
    return np.concatenate([np.sin(angles), np.cos(angles)], axis=1)
