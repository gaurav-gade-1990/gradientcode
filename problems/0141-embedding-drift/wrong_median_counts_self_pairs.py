import numpy as np


def _sqdist(a, b):
    d = (a * a).sum(1)[:, None] + (b * b).sum(1)[None, :] - 2.0 * a @ b.T
    return np.maximum(d, 0.0)


def embedding_drift(ref, cur, cos_threshold, mmd_threshold):
    x, y = np.asarray(ref, dtype=float), np.asarray(cur, dtype=float)
    n, m = len(x), len(y)

    mx, my = x.mean(0), y.mean(0)
    nx, ny = np.linalg.norm(mx), np.linalg.norm(my)
    cos_dist = 1.0 if nx == 0 or ny == 0 else 1.0 - float(mx @ my / (nx * ny))

    z = np.vstack([x, y])
    sigma = float(np.median(np.sqrt(_sqdist(z, z))))   # full matrix: self-pairs (zeros) and every pair twice
    if sigma == 0:
        sigma = 1.0

    def k(a, b):
        return np.exp(-_sqdist(a, b) / (2.0 * sigma ** 2))

    kxx, kyy, kxy = k(x, x), k(y, y), k(x, y)
    mmd2 = ((kxx.sum() - np.trace(kxx)) / (n * (n - 1))
            + (kyy.sum() - np.trace(kyy)) / (m * (m - 1))
            - 2.0 * kxy.mean())

    reasons = []
    if cos_dist > cos_threshold:
        reasons.append("centroid_shift")
    if mmd2 > mmd_threshold:
        reasons.append("mmd")
    return {"centroid_cosine_distance": cos_dist, "sigma": sigma, "mmd2": float(mmd2),
            "drifted": bool(reasons), "reasons": reasons}
