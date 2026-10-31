from collections import Counter

import numpy as np


def bm25_scores(docs, query, k1=1.5, b=0.75):
    toks = [d.lower().split() for d in docs]
    counts = [Counter(t) for t in toks]
    N = len(docs)
    dl = np.array([len(t) for t in toks], dtype=float)
    norm = k1 * (1 - b + b * dl / dl.mean())
    scores = np.zeros(N)
    for q in set(query.lower().split()):
        f = np.array([c[q] for c in counts], dtype=float)
        df = np.count_nonzero(f)
        idf = np.log(1 + (N - df + 0.5) / (df + 0.5))
        scores += idf * f * (k1 + 1) / (f + norm)
    return scores
