import numpy as np


def nesterov_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    # Uses the buffer from before this step's update in the look-ahead term.
    g = grad + weight_decay * param
    new_buf = momentum * buf + g
    param = param - lr * (g + momentum * buf)
    return param, new_buf
