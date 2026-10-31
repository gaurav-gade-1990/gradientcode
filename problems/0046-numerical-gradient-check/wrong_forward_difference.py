import numpy as np


def grad_check(f, x, analytic_grad, h=1e-5):
    num = np.zeros_like(x, dtype=float)
    fx = f(x)
    for idx in np.ndindex(x.shape):
        old = x[idx]
        x[idx] = old + h
        num[idx] = (f(x) - fx) / h
        x[idx] = old
    a = analytic_grad
    return num, float(np.linalg.norm(a - num) / max(np.linalg.norm(a) + np.linalg.norm(num), 1e-12))
