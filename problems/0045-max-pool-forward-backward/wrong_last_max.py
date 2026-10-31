import numpy as np


def maxpool(x, dout, pool_h, pool_w, stride):
    N, C, H, W = x.shape
    out_h = (H - pool_h) // stride + 1
    out_w = (W - pool_w) // stride + 1
    out = np.empty((N, C, out_h, out_w))
    dx = np.zeros_like(x, dtype=float)
    for n in range(N):
        for c in range(C):
            for y in range(out_h):
                for z in range(out_w):
                    h0, w0 = y * stride, z * stride
                    best, bi, bj = -np.inf, 0, 0
                    for i in range(pool_h):
                        for j in range(pool_w):
                            v = x[n, c, h0 + i, w0 + j]
                            if v >= best:              # >= keeps the LAST max on ties
                                best, bi, bj = v, i, j
                    out[n, c, y, z] = best
                    dx[n, c, h0 + bi, w0 + bj] += dout[n, c, y, z]
    return out, dx
