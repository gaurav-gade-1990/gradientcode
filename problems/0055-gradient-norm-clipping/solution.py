import numpy as np


def clip_grad_norm(grads, max_norm):
    total_norm = float(np.sqrt(sum(np.sum(g * g) for g in grads)))
    coef = min(1.0, max_norm / (total_norm + 1e-6))
    return [g * coef for g in grads], total_norm
