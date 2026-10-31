# Bug: multiplies by the reciprocal of the scale instead of dividing, so some exact .5 ties land a hair below or above and round the other way.
import numpy as np


def absmax_quantize(W: np.ndarray) -> tuple:
    absmax = np.max(np.abs(W), axis=1)
    scales = np.where(absmax > 0, absmax / 127.0, 1.0)
    x = W * (1.0 / scales[:, None])
    r = np.sign(x) * np.floor(np.abs(x) + 0.5)
    q = np.clip(r, -127, 127).astype(np.int8)
    W_hat = q.astype(np.float64) * scales[:, None]
    return q, scales, W_hat
