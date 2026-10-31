import numpy as np


def knn_predict(X_train, y_train, X_test, k):
    diff = X_test[:, None, :] - X_train[None, :, :]
    D = np.sum(diff * diff, axis=-1)
    n = len(X_train)
    # sort by distance, breaking ties by the HIGHER index
    nn = np.lexsort((-np.arange(n)[None, :].repeat(len(X_test), 0), D), axis=1)[:, :k]
    labels = y_train[nn]
    preds = []
    for row in labels:
        counts = np.bincount(row)
        top = counts.max()
        preds.append(next(l for l in row if counts[l] == top))
    return np.array(preds, dtype=np.int64)
