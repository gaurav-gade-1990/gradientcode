import numpy as np


def clip_grad_norm(grads, max_norm):
    # Clips each array by its own norm, which changes the direction of the overall gradient.
    clipped = []
    for g in grads:
        n = float(np.sqrt(np.sum(g * g)))
        clipped.append(g * min(1.0, max_norm / (n + 1e-6)))
    total_norm = float(np.sqrt(sum(np.sum(g * g) for g in grads)))
    return clipped, total_norm
