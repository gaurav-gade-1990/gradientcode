import numpy as np


def grouped_query_attention(q, k, v):
    n_q, n_kv = q.shape[1], k.shape[1]
    T, d = q.shape[2], q.shape[3]
    g = n_q // n_kv
    k = np.repeat(k, g, axis=1)
    v = np.repeat(v, g, axis=1)
    scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d)
    # Off by one: also hides the diagonal, except row 0 which would be empty.
    mask = np.triu(np.ones((T, T), dtype=bool), k=0)
    mask[0, 0] = False
    scores = np.where(mask, -np.inf, scores)
    scores = scores - scores.max(axis=-1, keepdims=True)
    w = np.exp(scores)
    return w / w.sum(axis=-1, keepdims=True) @ v
