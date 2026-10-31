import numpy as np


def layernorm(x, gamma, beta, dout, eps=1e-5):
    mu = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    inv_std = 1.0 / np.sqrt(var + eps)
    x_hat = (x - mu) * inv_std
    out = gamma * x_hat + beta

    lead = tuple(range(x.ndim - 1))            # every axis except the last
    dbeta = dout.sum(axis=lead)
    dgamma = (dout * x_hat).sum(axis=lead)

    g = dout * gamma
    dx = inv_std * (g - g.mean(axis=-1, keepdims=True)
                    - x_hat * (g * x_hat).mean(axis=-1, keepdims=True))
    return out, dx, dgamma, dbeta
