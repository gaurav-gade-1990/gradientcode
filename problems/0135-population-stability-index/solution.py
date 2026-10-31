import numpy as np


def _severity(psi):
    if psi < 0.1:
        return "stable"
    if psi < 0.25:
        return "moderate"
    return "major"


def psi_report(reference, current, n_bins=10, eps=1e-4):
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    edges = np.unique(np.quantile(ref, [i / n_bins for i in range(1, n_bins)]))
    n_bins_eff = len(edges) + 1
    ref_counts = np.bincount(np.searchsorted(edges, ref, side="left"), minlength=n_bins_eff)
    cur_counts = np.bincount(np.searchsorted(edges, cur, side="left"), minlength=n_bins_eff)
    r = np.maximum(ref_counts / len(ref), eps)
    c = np.maximum(cur_counts / len(cur), eps)
    contrib = (c - r) * np.log(c / r)
    psi = float(contrib.sum())
    return {
        "edges": [float(e) for e in edges],
        "ref_pct": [float(x) for x in r],
        "cur_pct": [float(x) for x in c],
        "contrib": [float(x) for x in contrib],
        "psi": psi,
        "severity": _severity(psi),
        "top_bin": int(np.argmax(contrib)),
    }
