import numpy as np


def sgd_momentum_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    g = grad + weight_decay * param
    buf = momentum * buf + g
    param = param - lr * buf
    return param, buf
