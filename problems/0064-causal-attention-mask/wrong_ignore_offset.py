import numpy as np


def causal_mask(T_q, T_k, offset=0):
    return np.where(np.tril(np.ones((T_q, T_k), dtype=bool)), 0.0, -np.inf)
