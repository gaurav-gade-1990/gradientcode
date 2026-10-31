import numpy as np


def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    conf = probs.max(axis=1)
    correct = (probs.argmax(axis=1) == labels).astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    # bin b holds edges[b] < conf <= edges[b+1]
    bins = np.searchsorted(edges[1:-1], conf, side="left")
    n = len(conf)
    count = np.bincount(bins, minlength=n_bins)
    sum_conf = np.bincount(bins, weights=conf, minlength=n_bins)
    sum_acc = np.bincount(bins, weights=correct, minlength=n_bins)
    nonempty = count > 0
    gap = np.abs(sum_acc[nonempty] - sum_conf[nonempty]) / count[nonempty]
    return float(np.sum(count[nonempty] / n * gap))
