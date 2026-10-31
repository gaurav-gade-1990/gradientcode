import numpy as np


def knn_predict(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, k: int) -> np.ndarray:
    diff = X_test[:, None, :] - X_train[None, :, :]
    D = np.sum(diff * diff, axis=-1)
    nn = np.argsort(D, axis=1, kind="stable")[:, :k]
    labels = y_train[nn]
    preds = np.empty(len(X_test), dtype=np.int64)
    for i, row in enumerate(labels):
        counts = np.bincount(row)
        top = counts.max()
        for lab in row:
            if counts[lab] == top:
                preds[i] = lab
                break
    return preds
