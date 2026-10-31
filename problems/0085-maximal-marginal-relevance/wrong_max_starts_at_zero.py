import numpy as np


def _unit(x):
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(n == 0, 1.0, n)


def mmr(query, docs, k, lam=0.5):
    D = _unit(docs)
    rel = D @ _unit(query)
    sim = D @ D.T
    n = len(docs)
    max_sim = np.zeros(n)
    chosen = np.zeros(n, dtype=bool)
    picks = []
    for _ in range(k):
        score = lam * rel - (1 - lam) * max_sim
        score[chosen] = -np.inf
        j = int(np.argmax(score))
        picks.append(j)
        chosen[j] = True
        max_sim = np.maximum(max_sim, sim[j])
    return np.array(picks, dtype=int)
