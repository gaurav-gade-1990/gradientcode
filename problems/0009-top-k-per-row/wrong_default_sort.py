# Bug: np.argsort without kind="stable" uses an unstable quicksort, so on rows longer than about 16
# entries equal values can come out in any index order instead of lowest index first.
import numpy as np


def top_k(x, k):
    idx = np.argsort(-x, axis=1)[:, :k]
    return np.take_along_axis(x, idx, axis=1), idx
