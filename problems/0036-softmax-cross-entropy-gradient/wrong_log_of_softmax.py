import numpy as np


def softmax_cross_entropy(logits, labels):
    N = logits.shape[0]
    z = logits - logits.max(axis=1, keepdims=True)
    p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
    rows = np.arange(N)
    loss = -np.log(p[rows, labels]).mean()
    d = p.copy()
    d[rows, labels] -= 1.0
    return float(loss), d / N
