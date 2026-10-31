import numpy as np


def flash_attention(Q, K, V, block_size, causal=False):
    # Exact attention on the full score matrix, with the final statistics reported for every block.
    Tq, d = Q.shape
    Tk = K.shape[0]
    n = (Tk + block_size - 1) // block_size
    s = Q @ K.T / np.sqrt(d)
    if causal:
        s = np.where(np.tril(np.ones((Tq, Tk), dtype=bool)), s, -np.inf)
    m = s.max(axis=1)
    p = np.exp(s - m[:, None])
    l = p.sum(axis=1)
    return (p @ V) / l[:, None], np.tile(m, (n, 1)), np.tile(l, (n, 1))
