import numpy as np


def absmax_quantize(W):
    absmax = np.max(np.abs(W))
    s = absmax / 127.0 if absmax > 0 else 1.0
    scales = np.full(W.shape[0], s)
    x = W / s
    q = np.clip(np.sign(x) * np.floor(np.abs(x) + 0.5), -127, 127).astype(np.int8)
    return q, scales, q.astype(np.float64) * s
