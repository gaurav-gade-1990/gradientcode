import numpy as np


def causal_mask(T_q, T_k, offset=0):
    i = np.arange(T_q)[:, None] + offset
    j = np.arange(T_k)[None, :]
    return np.where(j < i, 0.0, -np.inf)
