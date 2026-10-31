import numpy as np


def adagrad_step(param, grad, state_sum, lr=0.01, eps=1e-10, weight_decay=0.0):
    # Accumulates the raw gradient, then adds weight decay only to the step.
    state_sum = state_sum + grad * grad
    g = grad + weight_decay * param
    param = param - lr * g / (np.sqrt(state_sum) + eps)
    return param, state_sum
