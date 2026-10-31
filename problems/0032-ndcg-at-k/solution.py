import numpy as np


def ndcg_at_k(scores: np.ndarray, relevance: np.ndarray, k: int) -> np.ndarray:
    m = scores.shape[1]
    kk = min(k, m)
    discount = 1.0 / np.log2(np.arange(2, kk + 2))
    order = np.argsort(-scores, axis=1, kind="stable")[:, :kk]
    ranked = np.take_along_axis(relevance, order, axis=1).astype(float)
    dcg = ((2.0 ** ranked - 1.0) * discount).sum(axis=1)
    ideal = -np.sort(-relevance.astype(float), axis=1)[:, :kk]
    idcg = ((2.0 ** ideal - 1.0) * discount).sum(axis=1)
    return np.divide(dcg, idcg, out=np.zeros_like(dcg), where=idcg > 0)
