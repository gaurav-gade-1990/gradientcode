import numpy as np


def batchnorm_backward(dout, x, gamma, eps=1e-5):
    N = x.shape[0]
    mu = x.mean(axis=0)
    var = x.var(axis=0)
    inv_std = 1.0 / np.sqrt(var + eps)
    x_hat = (x - mu) * inv_std
    dbeta = dout.sum(axis=0)
    dgamma = (dout * x_hat).sum(axis=0)
    g = dout * gamma if x.ndim == 2 else dout * gamma[None, :, None, None]
    dx = inv_std / N * (N * g - g.sum(axis=0) - x_hat * (g * x_hat).sum(axis=0))
    if x.ndim == 4:
        dgamma, dbeta = dgamma.sum(axis=(1, 2)), dbeta.sum(axis=(1, 2))
    return dx, dgamma, dbeta
