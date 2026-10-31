import numpy as np


def sample_token(logits, temperature, top_k, top_p, u):
    z = logits / temperature
    p = np.exp(z - z.max())
    p = p / p.sum()
    order = np.argsort(-p, kind="stable")

    n_keep = len(p)
    if 0 < top_k < len(p):
        n_keep = top_k
    if top_p < 1.0:
        cum = np.cumsum(p[order])
        n_keep = min(n_keep, int(np.searchsorted(cum, top_p)) + 1)
    keep = np.zeros(len(p), dtype=bool)
    keep[order[:n_keep]] = True
    p = np.where(keep, p, 0.0)
    p = p / p.sum()

    token = int(np.searchsorted(np.cumsum(p), u, side="right"))
    return min(token, len(p) - 1), p
