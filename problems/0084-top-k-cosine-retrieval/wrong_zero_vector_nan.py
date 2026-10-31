import numpy as np


def top_k_cosine(queries, docs, k):
    q = queries / np.linalg.norm(queries, axis=1, keepdims=True)
    d = docs / np.linalg.norm(docs, axis=1, keepdims=True)
    S = q @ d.T
    idx = np.argsort(-S, axis=1, kind="stable")[:, :k]
    return idx, np.take_along_axis(S, idx, axis=1)
