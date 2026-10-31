import numpy as np


def rmsprop_step(param, grad, square_avg, lr=0.01, alpha=0.99, eps=1e-8, weight_decay=0.0):
    g = grad + weight_decay * param
    square_avg = alpha * square_avg + (1 - alpha) * g * g
    param = param - lr * g / np.sqrt(square_avg + eps)
    return param, square_avg
