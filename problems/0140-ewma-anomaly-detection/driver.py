def run(ns, series, alpha, k, warmup, min_std):
    """Stream the latency series through the detector; grade every score, flag and baseline update."""
    det = ns["EwmaDetector"](alpha, k, warmup, min_std)
    z, flags, mean, var, anomalies = [], [], [], [], []
    for i, x in enumerate(series):
        r = det.update(x)
        zi = r["z"]
        z.append(None if zi is None else float(zi))
        flags.append(bool(r["anomaly"]))
        if r["anomaly"]:
            anomalies.append(i)
        mean.append(float(det.mean))
        var.append(float(det.var))
    return {"anomalies": anomalies, "z": z, "flags": flags, "mean": mean, "var": var}
