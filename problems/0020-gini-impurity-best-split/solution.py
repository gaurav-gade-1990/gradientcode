import numpy as np


def gini(labels):
    if len(labels) == 0:
        return 0.0
    p = np.bincount(labels) / len(labels)
    return 1.0 - float(np.sum(p * p))


def best_split(X: np.ndarray, y: np.ndarray) -> tuple:
    n, d = X.shape
    best = (-1, 0.0, gini(y))
    best_score = None
    for j in range(d):
        v = np.unique(X[:, j])
        for t in (v[:-1] + v[1:]) / 2.0:
            left = X[:, j] <= t
            yl, yr = y[left], y[~left]
            score = len(yl) / n * gini(yl) + len(yr) / n * gini(yr)
            if best_score is None or score < best_score - 1e-12:
                best_score = score
                best = (j, float(t), float(score))
    return best
