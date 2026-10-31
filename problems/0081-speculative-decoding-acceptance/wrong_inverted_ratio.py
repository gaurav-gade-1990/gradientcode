import numpy as np


def sample(w, u):
    c = np.cumsum(w)
    return int(np.searchsorted(c, u * c[-1], side="right"))


def speculative_accept(draft_tokens, q, p, u_accept, u_sample):
    K = len(draft_tokens)
    tokens = []
    for i in range(K):
        x = int(draft_tokens[i])
        if p[i, x] > 0 and u_accept[i] < q[i, x] / p[i, x]:
            tokens.append(x)
            continue
        tokens.append(sample(np.maximum(0.0, p[i] - q[i]), u_sample[i]))
        return np.array(tokens), i
    tokens.append(sample(p[K], u_sample[K]))
    return np.array(tokens), K
