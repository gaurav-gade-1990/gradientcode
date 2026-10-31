import numpy as np


def knn_predict(X_train, y_train, X_test, k):
    diff = X_test[:, None, :] - X_train[None, :, :]
    D = np.sum(diff * diff, axis=-1)
    nn = np.argsort(D, axis=1, kind="stable")[:, :k]
    labels = y_train[nn]
    return np.array([np.bincount(row).argmax() for row in labels], dtype=np.int64)
