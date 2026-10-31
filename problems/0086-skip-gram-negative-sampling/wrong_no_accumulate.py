import numpy as np


def _sigmoid(x):
    e = np.exp(-np.abs(x))
    return np.where(x >= 0, 1 / (1 + e), e / (1 + e))


def sgns_loss_and_grads(W_in, W_out, center, context, negatives):
    negatives = np.asarray(negatives, dtype=int)
    v = W_in[center]
    u_o = W_out[context]
    U_neg = W_out[negatives]
    s_o = u_o @ v
    s_neg = U_neg @ v
    loss = np.logaddexp(0, -s_o) + np.sum(np.logaddexp(0, s_neg))
    g_o = _sigmoid(s_o) - 1
    g_neg = _sigmoid(s_neg)
    dW_in = np.zeros_like(W_in, dtype=float)
    dW_in[center] = g_o * u_o + g_neg @ U_neg
    dW_out = np.zeros_like(W_out, dtype=float)
    dW_out[context] = g_o * v
    dW_out[negatives] = g_neg[:, None] * v
    return float(loss), dW_in, dW_out
