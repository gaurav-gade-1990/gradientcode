import numpy as np


def _unit_rows(x):
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(n == 0, 1.0, n)


def top_k_cosine(queries, docs, k):
    S = _unit_rows(queries) @ _unit_rows(docs).T
    idx = np.argsort(S, axis=1, kind="stable")[:, ::-1][:, :k]
    return idx, np.take_along_axis(S, idx, axis=1)
