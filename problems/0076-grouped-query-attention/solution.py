import numpy as np


def grouped_query_attention(q: np.ndarray, k: np.ndarray, v: np.ndarray) -> np.ndarray:
    n_q, n_kv = q.shape[1], k.shape[1]
    T, d = q.shape[2], q.shape[3]
    g = n_q // n_kv
    k = np.repeat(k, g, axis=1)  # (B, n_q, T, d), head h -> kv head h // g
    v = np.repeat(v, g, axis=1)
    scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d)
    future = np.triu(np.ones((T, T), dtype=bool), k=1)
    scores = np.where(future, -np.inf, scores)
    scores = scores - scores.max(axis=-1, keepdims=True)
    w = np.exp(scores)
    w = w / w.sum(axis=-1, keepdims=True)
    return w @ v
