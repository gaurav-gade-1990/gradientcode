import numpy as np


def nesterov_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    # Classical momentum: steps along the buffer, no look-ahead term.
    g = grad + weight_decay * param
    buf = momentum * buf + g
    param = param - lr * buf
    return param, buf
