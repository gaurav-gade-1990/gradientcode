import numpy as np


def _average_ranks(s):
    """1-based ranks of s in ascending order; tied values share the mean of their ranks."""
    order = np.argsort(s, kind="stable")
    sorted_s = s[order]
    # start of each run of equal values
    starts = np.flatnonzero(np.r_[True, sorted_s[1:] != sorted_s[:-1]])
    ends = np.r_[starts[1:], len(s)]
    avg = (starts + ends + 1) / 2.0  # mean of ranks starts+1 .. ends
    ranks = np.empty(len(s))
    ranks[order] = np.repeat(avg, ends - starts)
    return ranks


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y_true) == 1
    ranks = _average_ranks(np.asarray(scores, dtype=float))
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    u = ranks[y].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))
