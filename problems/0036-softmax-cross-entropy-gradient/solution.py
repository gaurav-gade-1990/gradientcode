import numpy as np


def softmax_cross_entropy(logits: np.ndarray, labels: np.ndarray) -> tuple:
    N = logits.shape[0]
    z = logits - logits.max(axis=1, keepdims=True)
    log_sum = np.log(np.exp(z).sum(axis=1, keepdims=True))
    log_p = z - log_sum
    rows = np.arange(N)
    loss = -log_p[rows, labels].mean()
    dlogits = np.exp(log_p)
    dlogits[rows, labels] -= 1.0
    dlogits /= N
    return float(loss), dlogits
