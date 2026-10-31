import numpy as np


def softmax_cross_entropy(logits, labels):
    N = logits.shape[0]
    e = np.exp(logits)
    p = e / e.sum(axis=1, keepdims=True)
    rows = np.arange(N)
    loss = -(logits[rows, labels] - np.log(e.sum(axis=1))).mean()
    d = p.copy()
    d[rows, labels] -= 1.0
    return float(loss), d / N
