import numpy as np


def adagrad_step(param, grad, state_sum, lr=0.01, eps=1e-10, weight_decay=0.0):
    # Divides by the accumulator from before this step's gradient was added.
    g = grad + weight_decay * param
    param = param - lr * g / (np.sqrt(state_sum) + eps)
    state_sum = state_sum + g * g
    return param, state_sum
