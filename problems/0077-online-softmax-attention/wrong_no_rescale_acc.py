import numpy as np


def flash_attention(Q, K, V, block_size, causal=False):
    Tq, d = Q.shape
    Tk = K.shape[0]
    n = (Tk + block_size - 1) // block_size
    m, l, acc = np.full(Tq, -np.inf), np.zeros(Tq), np.zeros((Tq, V.shape[1]))
    mh, lh = np.zeros((n, Tq)), np.zeros((n, Tq))
    for b in range(n):
        j0, j1 = b * block_size, min((b + 1) * block_size, Tk)
        s = Q @ K[j0:j1].T / np.sqrt(d)
        if causal:
            s = np.where(np.arange(j0, j1)[None, :] <= np.arange(Tq)[:, None], s, -np.inf)
        m_new = np.maximum(m, s.max(axis=1))
        p = np.exp(s - m_new[:, None])
        l = np.exp(m - m_new) * l + p.sum(axis=1)
        acc = acc + p @ V[j0:j1]          # forgot to rescale the accumulator
        m = m_new
        mh[b], lh[b] = m, l
    return acc / l[:, None], mh, lh
