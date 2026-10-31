import numpy as np


def check(output, expected, args):
    if not isinstance(output, (tuple, list)) or len(output) != 2:
        return False, "expected a tuple (eigenvalue, eigenvector)"
    lam, v = output
    exp_lam, exp_v = expected
    ok, msg = compare(lam, exp_lam, 1e-6, 1e-8, "eigenvalue")
    if not ok:
        return ok, msg
    v = np.asarray(v, dtype=float)
    if v.shape != exp_v.shape:
        return False, "eigenvector: shape mismatch, expected %s, got %s" % (exp_v.shape, v.shape)
    if np.allclose(v, exp_v, rtol=1e-6, atol=1e-8) or np.allclose(v, -exp_v, rtol=1e-6, atol=1e-8):
        return True, ""
    ok, msg = compare(v, exp_v, 1e-6, 1e-8, "eigenvector")
    return False, msg + " (the sign of the eigenvector is ignored)"
