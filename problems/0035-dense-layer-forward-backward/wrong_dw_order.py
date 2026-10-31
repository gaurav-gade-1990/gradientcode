import numpy as np


def dense_forward_backward(x, W, b, dout):
    out = x @ W + b
    D, M = W.shape
    x2 = x.reshape(-1, D)
    d2 = dout.reshape(-1, M)
    dx = (d2 @ W.T).reshape(x.shape)
    dW = (d2.T @ x2).reshape(D, M)
    db = d2.sum(axis=0)
    return out, dx, dW, db
