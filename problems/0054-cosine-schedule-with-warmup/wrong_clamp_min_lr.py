import numpy as np


def cosine_lr(steps, base_lr, warmup_steps, total_steps, min_lr=0.0):
    # Decays toward 0 and clamps at min_lr instead of rescaling the cosine into [min_lr, base_lr].
    s = np.asarray(steps, dtype=float)
    warm = base_lr * s / max(1, warmup_steps)
    p = np.clip((s - warmup_steps) / max(1, total_steps - warmup_steps), 0.0, 1.0)
    cos = np.maximum(min_lr, base_lr * 0.5 * (1.0 + np.cos(np.pi * p)))
    return np.where(s < warmup_steps, warm, cos)
