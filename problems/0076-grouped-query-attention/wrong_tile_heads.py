import numpy as np


def grouped_query_attention(q, k, v):
    n_q, n_kv = q.shape[1], k.shape[1]
    T, d = q.shape[2], q.shape[3]
    g = n_q // n_kv
    k = np.tile(k, (1, g, 1, 1))
    v = np.tile(v, (1, g, 1, 1))
    scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d)
    scores = np.where(np.triu(np.ones((T, T), dtype=bool), k=1), -np.inf, scores)
    scores = scores - scores.max(axis=-1, keepdims=True)
    w = np.exp(scores)
    return w / w.sum(axis=-1, keepdims=True) @ v
