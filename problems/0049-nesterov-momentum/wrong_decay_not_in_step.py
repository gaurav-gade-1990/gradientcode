import numpy as np


def nesterov_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    # Decay feeds the buffer, but the raw gradient is used in the step's g term.
    g = grad + weight_decay * param
    buf = momentum * buf + g
    param = param - lr * (grad + momentum * buf)
    return param, buf
