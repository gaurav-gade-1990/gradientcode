import numpy as np


def run(ns, expr, x, analytic_grad, h=1e-5):
    """Build f from `expr`, call your grad_check, and report the gradient, the error and x afterwards."""
    def f(v):
        return float(eval(expr, {"__builtins__": {}, "np": np}, {"x": v}))

    xs = np.array(x, dtype=float)
    num, rel = ns["grad_check"](f, xs, np.array(analytic_grad, dtype=float), h)
    return {"num_grad": np.asarray(num, dtype=float), "rel_error": float(rel), "x_after": xs}
