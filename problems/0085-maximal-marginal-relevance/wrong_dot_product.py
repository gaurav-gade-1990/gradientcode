import numpy as np


def mmr(query, docs, k, lam=0.5):
    rel = docs @ query
    sim = docs @ docs.T
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
        max_sim = sim[j] if len(picks) == 1 else np.maximum(max_sim, sim[j])
    return np.array(picks, dtype=int)
