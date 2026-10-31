import numpy as np


def sgd_momentum_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    # CS231n form: the buffer stores -lr * (running gradient sum), not PyTorch's buffer.
    g = grad + weight_decay * param
    buf = momentum * buf - lr * g
    param = param + buf
    return param, buf
