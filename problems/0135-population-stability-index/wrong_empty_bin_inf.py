import numpy as np


def psi_report(reference, current, n_bins=10, eps=1e-4):
    # Incident: a bin with no traffic today gave log(0); the dashboard showed PSI = inf / NaN
    # and the alert rule (psi >= 0.25) silently never fired on NaN.
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    edges = np.unique(np.quantile(ref, [i / n_bins for i in range(1, n_bins)]))
    b = len(edges) + 1
    r = np.bincount(np.searchsorted(edges, ref, side="left"), minlength=b) / len(ref)
    c = np.bincount(np.searchsorted(edges, cur, side="left"), minlength=b) / len(cur)
    with np.errstate(divide="ignore", invalid="ignore"):
        contrib = (c - r) * np.log(c / r)
    psi = float(contrib.sum())
    sev = "stable" if psi < 0.1 else ("moderate" if psi < 0.25 else "major")
    return {"edges": [float(e) for e in edges], "ref_pct": [float(x) for x in r], "cur_pct": [float(x) for x in c],
            "contrib": [float(x) for x in contrib], "psi": psi, "severity": sev, "top_bin": int(np.nanargmax(contrib))}
