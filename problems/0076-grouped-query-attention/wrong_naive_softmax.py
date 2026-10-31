import numpy as np


def grouped_query_attention(q, k, v):
    n_q, n_kv = q.shape[1], k.shape[1]
    T, d = q.shape[2], q.shape[3]
    g = n_q // n_kv
    k = np.repeat(k, g, axis=1)
    v = np.repeat(v, g, axis=1)
    scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d)
    w = np.exp(scores) * np.tril(np.ones((T, T)))
    return w / w.sum(axis=-1, keepdims=True) @ v
