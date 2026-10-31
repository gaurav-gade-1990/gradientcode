import numpy as np


def maxpool(x, dout, pool_h, pool_w, stride):
    N, C, H, W = x.shape
    out_h = (H - pool_h) // stride + 1
    out_w = (W - pool_w) // stride + 1
    out = np.empty((N, C, out_h, out_w))
    dx = np.zeros_like(x, dtype=float)
    for y in range(out_h):
        for z in range(out_w):
            h0, w0 = y * stride, z * stride
            win = x[:, :, h0:h0 + pool_h, w0:w0 + pool_w]
            m = win.max(axis=(2, 3), keepdims=True)
            out[:, :, y, z] = m[:, :, 0, 0]
            # Every position equal to the max gets the gradient.
            dx[:, :, h0:h0 + pool_h, w0:w0 + pool_w] += (win == m) * dout[:, :, y, z][:, :, None, None]
    return out, dx
