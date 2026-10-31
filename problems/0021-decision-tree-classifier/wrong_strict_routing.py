import numpy as np


def gini(labels):
    p = np.bincount(labels) / len(labels)
    return 1.0 - float(np.sum(p * p))


def best_split(X, y):
    n, d = X.shape
    best, best_score = None, None
    for j in range(d):
        v = np.unique(X[:, j])
        for t in (v[:-1] + v[1:]) / 2.0:
            left = X[:, j] <= t
            yl, yr = y[left], y[~left]
            score = len(yl) / n * gini(yl) + len(yr) / n * gini(yr)
            if best_score is None or score < best_score - 1e-12:
                best_score, best = score, (j, float(t))
    return best


def build(X, y, depth, max_depth, min_samples_split):
    leaf = ("leaf", int(np.bincount(y).argmax()))
    if depth == max_depth or len(y) < min_samples_split or np.all(y == y[0]):
        return leaf
    split = best_split(X, y)
    if split is None:
        return leaf
    j, t = split
    m = X[:, j] <= t
    return ("split", j, t,
            build(X[m], y[m], depth + 1, max_depth, min_samples_split),
            build(X[~m], y[~m], depth + 1, max_depth, min_samples_split))


def predict_one(node, x):
    while node[0] == "split":
        _, j, t, left, right = node
        node = left if x[j] < t else right
    return node[1]


def decision_tree_predict(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, max_depth: int, min_samples_split: int = 2) -> np.ndarray:
    tree = build(X_train, y_train, 0, max_depth, min_samples_split)
    return np.array([predict_one(tree, x) for x in X_test], dtype=np.int64)
