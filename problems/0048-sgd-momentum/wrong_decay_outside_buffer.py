import numpy as np


def sgd_momentum_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    # Applies weight decay to the step but keeps it out of the buffer.
    buf = momentum * buf + grad
    param = param - lr * (buf + weight_decay * param)
    return param, buf
