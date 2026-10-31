import numpy as np


def grad_check(f, x, analytic_grad, h=1e-5):
    num = np.zeros_like(x, dtype=float)
    for idx in np.ndindex(x.shape):
        x[idx] += h
        f_plus = f(x)
        x[idx] -= 2 * h
        f_minus = f(x)
        # forgot: x[idx] += h
        num[idx] = (f_plus - f_minus) / (2 * h)
    a = analytic_grad
    return num, float(np.linalg.norm(a - num) / max(np.linalg.norm(a) + np.linalg.norm(num), 1e-12))
