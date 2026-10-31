import numpy as np


def absmax_quantize(W):
    absmax = np.max(np.abs(W), axis=1)
    scales = np.where(absmax > 0, absmax / 127.0, 1.0)
    q = np.clip(np.floor(W / scales[:, None] + 0.5), -127, 127).astype(np.int8)
    return q, scales, q.astype(np.float64) * scales[:, None]
