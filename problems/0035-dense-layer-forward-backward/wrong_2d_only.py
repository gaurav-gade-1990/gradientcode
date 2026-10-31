import numpy as np


def dense_forward_backward(x, W, b, dout):
    out = x @ W + b
    dx = dout @ W.T
    dW = x.T @ dout
    db = dout.sum(axis=0)
    return out, dx, dW, db
