import numpy as np


def layernorm(x, gamma, beta, dout, eps=1e-5):
    # Batch-norm habit: statistics over axis 0.
    mu = x.mean(axis=0, keepdims=True)
    var = x.var(axis=0, keepdims=True)
    inv_std = 1.0 / np.sqrt(var + eps)
    x_hat = (x - mu) * inv_std
    out = gamma * x_hat + beta
    lead = tuple(range(x.ndim - 1))
    g = dout * gamma
    dx = inv_std * (g - g.mean(axis=0, keepdims=True) - x_hat * (g * x_hat).mean(axis=0, keepdims=True))
    return out, dx, (dout * x_hat).sum(axis=lead), dout.sum(axis=lead)
