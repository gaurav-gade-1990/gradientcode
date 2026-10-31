import numpy as np


def _unit(x):
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(n == 0, 1.0, n)


def mmr(query: np.ndarray, docs: np.ndarray, k: int, lam: float = 0.5) -> np.ndarray:
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
        max_sim = sim[j] if len(picks) == 1 else np.maximum(max_sim, sim[j])
    return np.array(picks, dtype=int)
