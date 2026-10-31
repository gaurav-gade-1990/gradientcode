import numpy as np


def stratified_k_fold(y, k):
    return np.arange(len(y)) % k
