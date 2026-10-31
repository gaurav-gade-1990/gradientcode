import numpy as np


def batchnorm_forward(x, gamma, beta, running_mean, running_var, momentum=0.9, eps=1e-5, train=True):
    if train:
        mu, var = x.mean(axis=0), x.var(axis=0)
        new_mean = (1 - momentum) * running_mean + momentum * mu
        new_var = (1 - momentum) * running_var + momentum * var
    else:
        mu, var = running_mean, running_var
        new_mean, new_var = running_mean.copy(), running_var.copy()
    return gamma * (x - mu) / np.sqrt(var + eps) + beta, new_mean, new_var
