import numpy as np


def one_hot(labels, num_classes):
    c = int(labels.max()) + 1 if labels.size else num_classes
    out = np.zeros((labels.shape[0], c))
    out[np.arange(labels.shape[0]), labels] = 1.0
    return out
