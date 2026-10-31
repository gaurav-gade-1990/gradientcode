import numpy as np


def dropout(x, keep_prob, u, train=True):
    # Classic (non-inverted) dropout habit: scale at test time.
    if not train:
        return x * keep_prob
    return x * (u < keep_prob) / keep_prob
