import numpy as np


def softmax_cross_entropy(logits, labels):
    N = logits.shape[0]
    z = logits - logits.max(axis=1, keepdims=True)
    log_p = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
    rows = np.arange(N)
    loss = -log_p[rows, labels].mean()
    d = np.exp(log_p)
    d[rows, labels] -= 1.0
    return float(loss), d
