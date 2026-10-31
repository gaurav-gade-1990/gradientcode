import numpy as np


def sample(w, u):
    c = np.cumsum(w)
    return int(np.searchsorted(c, u * c[-1], side="right"))


def speculative_accept(draft_tokens, q, p, u_accept, u_sample):
    K = len(draft_tokens)
    tokens = []
    for i in range(K):
        x = int(draft_tokens[i])
        if u_accept[i] < p[i, x] / q[i, x]:
            tokens.append(x)
            continue
        residual = np.maximum(0.0, p[i] - q[i])
        tokens.append(sample(residual, u_sample[i]))
        return np.array(tokens, dtype=np.int64), i
    tokens.append(sample(p[K], u_sample[K]))
    return np.array(tokens, dtype=np.int64), K
