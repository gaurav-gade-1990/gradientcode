import numpy as np


def attention(q, k, v, mask=None):
    d_k = q.shape[-1]
    scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d_k)
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)
    e = np.exp(scores)
    weights = e / np.sum(e, axis=-1, keepdims=True)
    return weights @ v, weights
