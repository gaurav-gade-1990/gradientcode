import numpy as np


def absmax_quantize(W):
    scales = np.max(np.abs(W), axis=1) / 127.0
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.nan_to_num(W / scales[:, None])
    q = np.clip(np.sign(x) * np.floor(np.abs(x) + 0.5), -127, 127).astype(np.int8)
    return q, scales, q.astype(np.float64) * scales[:, None]
