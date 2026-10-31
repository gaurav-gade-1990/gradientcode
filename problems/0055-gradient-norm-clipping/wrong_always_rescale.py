import numpy as np


def clip_grad_norm(grads, max_norm):
    # Forgets the clamp at 1, so small gradients get scaled UP to max_norm.
    total_norm = float(np.sqrt(sum(np.sum(g * g) for g in grads)))
    coef = max_norm / (total_norm + 1e-6)
    return [g * coef for g in grads], total_norm
