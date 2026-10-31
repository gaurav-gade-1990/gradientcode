import numpy as np


def sgd_momentum_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    # Treats the buffer like Adam's first moment: an EMA with a (1 - momentum) factor.
    g = grad + weight_decay * param
    buf = momentum * buf + (1 - momentum) * g
    param = param - lr * buf
    return param, buf
