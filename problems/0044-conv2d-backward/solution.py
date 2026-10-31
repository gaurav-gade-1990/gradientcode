import numpy as np


def conv2d_backward(dout, x, w, stride=1, pad=0):
    N, C, H, W = x.shape
    F, _, kh, kw = w.shape
    _, _, out_h, out_w = dout.shape
    xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
    dxp = np.zeros_like(xp)
    dw = np.zeros_like(w)
    for i in range(kh):
        for j in range(kw):
            hs = slice(i, i + stride * out_h, stride)
            ws = slice(j, j + stride * out_w, stride)
            dw[:, :, i, j] = np.einsum("nfhw,nchw->fc", dout, xp[:, :, hs, ws])
            # Windows overlap when stride < kernel size: accumulate.
            dxp[:, :, hs, ws] += np.einsum("nfhw,fc->nchw", dout, w[:, :, i, j])
    dx = dxp[:, :, pad:pad + H, pad:pad + W]
    db = dout.sum(axis=(0, 2, 3))
    return dx, dw, db
