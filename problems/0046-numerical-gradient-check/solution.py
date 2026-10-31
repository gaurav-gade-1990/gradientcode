import numpy as np


def grad_check(f, x: np.ndarray, analytic_grad: np.ndarray, h: float = 1e-5) -> tuple:
    num = np.zeros_like(x, dtype=float)
    for idx in np.ndindex(x.shape):
        old = x[idx]
        x[idx] = old + h
        f_plus = f(x)
        x[idx] = old - h
        f_minus = f(x)
        x[idx] = old                     # restore
        num[idx] = (f_plus - f_minus) / (2 * h)
    a = analytic_grad
    denom = max(np.linalg.norm(a) + np.linalg.norm(num), 1e-12)
    return num, float(np.linalg.norm(a - num) / denom)
