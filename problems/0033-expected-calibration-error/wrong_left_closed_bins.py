import numpy as np


def expected_calibration_error(probs, labels, n_bins=10):
    conf = probs.max(axis=1)
    correct = (probs.argmax(axis=1) == labels).astype(float)
    bins = np.minimum((conf * n_bins).astype(int), n_bins - 1)
    count = np.bincount(bins, minlength=n_bins)
    sum_conf = np.bincount(bins, weights=conf, minlength=n_bins)
    sum_acc = np.bincount(bins, weights=correct, minlength=n_bins)
    ne = count > 0
    return float(np.sum(np.abs(sum_acc[ne] - sum_conf[ne])) / len(conf))
