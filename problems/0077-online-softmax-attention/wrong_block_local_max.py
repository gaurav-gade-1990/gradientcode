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
        bmax = s.max(axis=1)
        m_new = np.maximum(m, bmax)
        p = np.exp(s - m_new[:, None])
        corr = np.exp(m - m_new)
        l = corr * l + p.sum(axis=1)
        acc = corr[:, None] * acc + p @ V[j0:j1]
        m = m_new
        mh[b], lh[b] = bmax, l        # records the block's own max, not the running max
    return acc / l[:, None], mh, lh
