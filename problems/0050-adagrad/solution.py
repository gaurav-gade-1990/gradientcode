import numpy as np


def adagrad_step(param, grad, state_sum, lr=0.01, eps=1e-10, weight_decay=0.0):
    g = grad + weight_decay * param
    state_sum = state_sum + g * g
    param = param - lr * g / (np.sqrt(state_sum) + eps)
    return param, state_sum
