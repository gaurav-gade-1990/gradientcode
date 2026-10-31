import numpy as np


def expected_calibration_error(probs, labels, n_bins=10):
    conf = probs.max(axis=1)
    correct = (probs.argmax(axis=1) == labels).astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = np.searchsorted(edges[1:-1], conf, side="left")
    gaps = []
    for b in range(n_bins):
        sel = bins == b
        if sel.any():
            gaps.append(abs(correct[sel].mean() - conf[sel].mean()))
    return float(np.mean(gaps))
