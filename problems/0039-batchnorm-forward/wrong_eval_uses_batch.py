import numpy as np


def batchnorm_forward(x, gamma, beta, running_mean, running_var, momentum=0.9, eps=1e-5, train=True):
    mu, var = x.mean(axis=0), x.var(axis=0)
    if train:
        new_mean = momentum * running_mean + (1 - momentum) * mu
        new_var = momentum * running_var + (1 - momentum) * var
    else:
        new_mean, new_var = running_mean.copy(), running_var.copy()
    return gamma * (x - mu) / np.sqrt(var + eps) + beta, new_mean, new_var
