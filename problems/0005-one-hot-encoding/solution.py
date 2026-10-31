import numpy as np


def one_hot(labels: np.ndarray, num_classes: int) -> np.ndarray:
    labels = np.asarray(labels, dtype=int)
    out = np.zeros((labels.shape[0], num_classes), dtype=np.float64)
    out[np.arange(labels.shape[0]), labels] = 1.0
    return out
