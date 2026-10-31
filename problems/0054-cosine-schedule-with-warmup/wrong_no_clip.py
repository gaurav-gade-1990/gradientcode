import numpy as np


def cosine_lr(steps, base_lr, warmup_steps, total_steps, min_lr=0.0):
    # Past total_steps the cosine climbs back up.
    s = np.asarray(steps, dtype=float)
    warm = base_lr * s / max(1, warmup_steps)
    p = (s - warmup_steps) / max(1, total_steps - warmup_steps)
    cos = min_lr + (base_lr - min_lr) * 0.5 * (1.0 + np.cos(np.pi * p))
    return np.where(s < warmup_steps, warm, cos)
