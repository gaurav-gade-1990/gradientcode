import numpy as np


def flash_attention(Q, K, V, block_size, causal=False):
    Tq, d = Q.shape
    Tk = K.shape[0]
    n_blocks = (Tk + block_size - 1) // block_size
    m = np.full(Tq, -np.inf)
    l = np.zeros(Tq)
    acc = np.zeros((Tq, V.shape[1]))
    m_hist = np.zeros((n_blocks, Tq))
    l_hist = np.zeros((n_blocks, Tq))
    rows = np.arange(Tq)[:, None]

    for b in range(n_blocks):
        j0, j1 = b * block_size, min((b + 1) * block_size, Tk)
        s = Q @ K[j0:j1].T / np.sqrt(d)                  # (Tq, block)
        if causal:
            s = np.where(np.arange(j0, j1)[None, :] <= rows, s, -np.inf)
        m_new = np.maximum(m, s.max(axis=1))             # finite: key 0 is in block 0
        p = np.exp(s - m_new[:, None])                   # masked entries -> 0
        corr = np.exp(m - m_new)                         # 0 on the first block
        l = corr * l + p.sum(axis=1)
        acc = corr[:, None] * acc + p @ V[j0:j1]
        m = m_new
        m_hist[b] = m
        l_hist[b] = l

    return acc / l[:, None], m_hist, l_hist
