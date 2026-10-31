import numpy as np


def batchnorm_backward(dout, x, gamma, eps=1e-5):
    if x.ndim == 2:
        axes, shape = (0,), (1, -1)
    else:
        axes, shape = (0, 2, 3), (1, -1, 1, 1)
    mu = x.mean(axis=axes, keepdims=True)
    var = x.var(axis=axes, keepdims=True)
    inv_std = 1.0 / np.sqrt(var + eps)
    x_hat = (x - mu) * inv_std

    dbeta = dout.sum(axis=axes)
    dgamma = (dout * x_hat).sum(axis=axes)

    g = dout * gamma.reshape(shape)            # dL/dx_hat
    dx = inv_std * (g - g.mean(axis=axes, keepdims=True)
                    - x_hat * (g * x_hat).mean(axis=axes, keepdims=True))
    return dx, dgamma, dbeta
