import numpy as np


def grouped_query_attention(q, k, v):
    n_q, n_kv = q.shape[1], k.shape[1]
    T = q.shape[2]
    g = n_q // n_kv
    k = np.repeat(k, g, axis=1)
    v = np.repeat(v, g, axis=1)
    scores = q @ np.swapaxes(k, -1, -2)
    scores = np.where(np.triu(np.ones((T, T), dtype=bool), k=1), -np.inf, scores)
    scores = scores - scores.max(axis=-1, keepdims=True)
    w = np.exp(scores)
    return w / w.sum(axis=-1, keepdims=True) @ v
