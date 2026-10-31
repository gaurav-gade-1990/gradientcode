import numpy as np


def im2col(x, kh, kw, stride=1, pad=0):
    N, C, H, W = x.shape
    xp = np.pad(x, ((0, 0), (0, 0), (0, 2 * pad), (0, 2 * pad)))
    out_h = (H + 2 * pad - kh) // stride + 1
    out_w = (W + 2 * pad - kw) // stride + 1
    patches = np.empty((N, C, kh, kw, out_h, out_w), dtype=x.dtype)
    for i in range(kh):
        for j in range(kw):
            patches[:, :, i, j] = xp[:, :, i:i + stride * out_h:stride, j:j + stride * out_w:stride]
    return patches.transpose(1, 2, 3, 0, 4, 5).reshape(C * kh * kw, -1)
