import numpy as np


def maxpool(x, dout, pool_h, pool_w, stride):
    N, C, H, W = x.shape
    out_h = (H - pool_h) // stride + 1
    out_w = (W - pool_w) // stride + 1
    out = np.empty((N, C, out_h, out_w))
    dx = np.zeros_like(x, dtype=float)
    n_idx, c_idx = np.meshgrid(np.arange(N), np.arange(C), indexing="ij")
    for y in range(out_h):
        for z in range(out_w):
            h0, w0 = y * stride, z * stride
            win = x[:, :, h0:h0 + pool_h, w0:w0 + pool_w].reshape(N, C, -1)
            k = win.argmax(axis=2)
            out[:, :, y, z] = win.max(axis=2)
            dx[n_idx, c_idx, h0 + k // pool_w, w0 + k % pool_w] = dout[:, :, y, z]
    return out, dx
