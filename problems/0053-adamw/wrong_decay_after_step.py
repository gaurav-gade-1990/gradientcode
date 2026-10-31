import numpy as np


def adamw_step(param, grad, m, v, t, lr=1e-3, beta1=0.9, beta2=0.999, eps=1e-8, weight_decay=1e-2):
    # Decays the already-updated parameters, so the Adam step gets shrunk too.
    m = beta1 * m + (1 - beta1) * grad
    v = beta2 * v + (1 - beta2) * grad * grad
    m_hat = m / (1 - beta1 ** t)
    v_hat = v / (1 - beta2 ** t)
    param = param - lr * m_hat / (np.sqrt(v_hat) + eps)
    param = param * (1 - lr * weight_decay)
    return param, m, v
