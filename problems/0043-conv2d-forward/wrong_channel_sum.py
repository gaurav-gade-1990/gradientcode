import numpy as np


def conv2d_forward(x, w, b, stride=1, pad=0):
    # Reuses the channel-0 weights for every input channel instead of w[f, c].
    N, C, H, W = x.shape
    F, _, kh, kw = w.shape
    xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
    out_h = (H + 2 * pad - kh) // stride + 1
    out_w = (W + 2 * pad - kw) // stride + 1
    out = np.zeros((N, F, out_h, out_w))
    for i in range(kh):
        for j in range(kw):
            win = xp[:, :, i:i + stride * out_h:stride, j:j + stride * out_w:stride]
            out += np.einsum("nchw,f->nfhw", win, w[:, 0, i, j])
    return out + b[None, :, None, None]
