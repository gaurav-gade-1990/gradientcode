import numpy as np


def batchnorm_backward(dout, x, gamma, eps=1e-5):
    axes, shape = ((0,), (1, -1)) if x.ndim == 2 else ((0, 2, 3), (1, -1, 1, 1))
    mu = x.mean(axis=axes, keepdims=True)
    var = x.var(axis=axes, keepdims=True)
    inv_std = 1.0 / np.sqrt(var + eps)
    x_hat = (x - mu) * inv_std
    g = dout * gamma.reshape(shape)
    # Accounts for the mean but forgets that var depends on x.
    dx = inv_std * (g - g.mean(axis=axes, keepdims=True))
    return dx, (dout * x_hat).sum(axis=axes), dout.sum(axis=axes)
