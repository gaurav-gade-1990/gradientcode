import numpy as np


def top_k_cosine(queries, docs, k):
    S = queries @ docs.T
    idx = np.argsort(-S, axis=1, kind="stable")[:, :k]
    return idx, np.take_along_axis(S, idx, axis=1)
