import numpy as np


def sliding_windows(x, window, stride):
    starts = np.arange(0, len(x) - window, stride)
    idx = starts[:, None] + np.arange(window)[None, :]
    return x[idx].reshape(-1, window)
