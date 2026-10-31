from collections import Counter

import numpy as np


def bm25_scores(docs: list, query: str, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
    toks = [d.lower().split() for d in docs]
    counts = [Counter(t) for t in toks]
    N = len(docs)
    dl = np.array([len(t) for t in toks], dtype=float)
    norm = k1 * (1 - b + b * dl / dl.mean())

    scores = np.zeros(N)
    for q in query.lower().split():
        f = np.array([c[q] for c in counts], dtype=float)
        df = np.count_nonzero(f)
        idf = np.log(1 + (N - df + 0.5) / (df + 0.5))
        scores += idf * f * (k1 + 1) / (f + norm)
    return scores
