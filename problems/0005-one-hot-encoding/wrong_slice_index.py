import numpy as np


def one_hot(labels, num_classes):
    out = np.zeros((labels.shape[0], num_classes))
    out[:, labels] = 1.0
    return out
