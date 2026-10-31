import numpy as np


def run(ns, A=None, B=None, seed=None, n=0, m=0, d=0):
    """Small cases pass A and B and compare the full matrix.
    The large timing case builds A and B from a seed and compares a summary, to keep the test file small."""
    f = ns["pairwise_distances"]
    if seed is None:
        return np.asarray(f(A, B), dtype=float)
    rng = np.random.default_rng(seed)
    A = rng.normal(size=(n, d))
    B = rng.normal(size=(m, d))
    D = np.asarray(f(A, B), dtype=float)
    return {
        "shape": tuple(int(s) for s in D.shape),
        "row_sums": D.sum(axis=1),
        "col_sums": D.sum(axis=0),
        "sample": D[::97, ::89],
        "has_nan": bool(np.isnan(D).any()),
    }
