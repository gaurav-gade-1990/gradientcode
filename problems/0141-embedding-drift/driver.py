import numpy as np

from gc_runtime import embed


def run(ns, reference, current, cos_threshold, mmd_threshold):
    """Embed both ticket windows with the judge's embedding model and grade the drift report."""
    ref = np.array([embed(t, dim=32) for t in reference])
    cur = np.array([embed(t, dim=32) for t in current])
    out = ns["embedding_drift"](ref, cur, cos_threshold, mmd_threshold)
    return {
        "centroid_cosine_distance": float(out["centroid_cosine_distance"]),
        "sigma": float(out["sigma"]),
        "mmd2": float(out["mmd2"]),
        "drifted": bool(out["drifted"]),
        "reasons": list(out["reasons"]),
    }
