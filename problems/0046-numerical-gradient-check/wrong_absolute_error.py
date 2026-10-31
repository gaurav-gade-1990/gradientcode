import numpy as np


def grad_check(f, x, analytic_grad, h=1e-5):
    num = np.zeros_like(x, dtype=float)
    for idx in np.ndindex(x.shape):
        old = x[idx]
        x[idx] = old + h
        f_plus = f(x)
        x[idx] = old - h
        f_minus = f(x)
        x[idx] = old
        num[idx] = (f_plus - f_minus) / (2 * h)
    return num, float(np.linalg.norm(analytic_grad - num))
