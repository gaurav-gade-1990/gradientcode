import numpy as np


def conv2d_backward(dout, x, w, stride=1, pad=0):
    N, C, H, W = x.shape
    F, _, kh, kw = w.shape
    _, _, out_h, out_w = dout.shape
    xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
    dxp = np.zeros_like(xp)
    dw = np.zeros_like(w)
    wf = w[:, :, ::-1, ::-1]
    for i in range(kh):
        for j in range(kw):
            hs = slice(i, i + stride * out_h, stride)
            ws = slice(j, j + stride * out_w, stride)
            dw[:, :, i, j] = np.einsum("nfhw,nchw->fc", dout, xp[:, :, hs, ws])
            # "dx is a convolution with the flipped kernel" applied in the wrong frame.
            dxp[:, :, hs, ws] += np.einsum("nfhw,fc->nchw", dout, wf[:, :, i, j])
    return dxp[:, :, pad:pad + H, pad:pad + W], dw, dout.sum(axis=(0, 2, 3))
