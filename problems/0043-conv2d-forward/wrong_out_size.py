import numpy as np


def conv2d_forward(x, w, b, stride=1, pad=0):
    N, C, H, W = x.shape
    F, _, kh, kw = w.shape
    xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
    # Rounds up instead of down when the stride does not divide evenly.
    out_h = -(-(H + 2 * pad - kh) // stride) + 1
    out_w = -(-(W + 2 * pad - kw) // stride) + 1
    out = np.zeros((N, F, out_h, out_w))
    for y in range(out_h):
        for z in range(out_w):
            win = xp[:, :, y * stride:y * stride + kh, z * stride:z * stride + kw]
            win = np.pad(win, ((0, 0), (0, 0), (0, kh - win.shape[2]), (0, kw - win.shape[3])))
            out[:, :, y, z] = np.einsum("nchw,fchw->nf", win, w)
    return out + b[None, :, None, None]
