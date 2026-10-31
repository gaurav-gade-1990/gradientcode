import numpy as np


def _trace(rng, n, base, noise):
    return [round(float(v), 1) for v in base + noise * rng.standard_normal(n)]


def cases():
    rng = np.random.default_rng(140)
    steady = _trace(rng, 120, 85.0, 4.0)
    spiky = list(steady)
    for i, bump in ((40, 60.0), (41, 75.0), (90, -50.0)):
        spiky[i] = round(spiky[i] + bump, 1)
    shift = _trace(rng, 60, 80.0, 3.0) + _trace(rng, 40, 140.0, 3.0)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"series": [82.0, 84.0, 83.0, 85.0, 84.0, 140.0, 83.0], "alpha": 0.3, "k": 3.0, "warmup": 3, "min_std": 1.0},
         "explanation": "Indices 0-2 only learn: mean 82 -> 82.6 -> 82.72, var 0 -> 0.84 -> 0.618. From index 3 each point is scored against the baseline "
                        "before it. Index 5 (a GPU node falling over, 140 ms) scores z = (140 - 83.58) / 1.069 = 52.8 and is flagged, and the baseline is NOT moved by it, "
                        "so index 6 at 83 ms scores as normal."},
        {"name": "Example 2", "hidden": False,
         "args": {"series": [50.0, 50.0, 50.0, 50.0, 50.5, 49.6, 59.0], "alpha": 0.2, "k": 4.0, "warmup": 2, "min_std": 2.0},
         "explanation": "A cache-backed endpoint is perfectly flat, so var is 0. The min_std floor of 2 ms means a 0.5 ms wobble scores z = 0.25, "
                        "not infinity. 59 ms is z = 9 / 2 = 4.5 against the floor and crosses k = 4, so it is flagged and the mean stays at 50."},
        {"name": "steady traffic no anomalies", "args": {"series": steady, "alpha": 0.1, "k": 4.0, "warmup": 10, "min_std": 1.0}},
        {"name": "spikes do not poison the baseline", "args": {"series": spiky, "alpha": 0.1, "k": 4.0, "warmup": 10, "min_std": 1.0}},
        {"name": "level shift stays anomalous", "args": {"series": shift, "alpha": 0.2, "k": 3.5, "warmup": 15, "min_std": 1.0}},
        {"name": "flat series with tiny wobble",
         "args": {"series": [120.0] * 12 + [120.3, 119.8, 120.0, 121.0, 120.0], "alpha": 0.25, "k": 3.0, "warmup": 5, "min_std": 0.5}},
        {"name": "outlier inside warmup is learned",
         "args": {"series": [70.0, 72.0, 300.0, 71.0, 69.0, 73.0, 70.0, 250.0, 71.0], "alpha": 0.3, "k": 3.0, "warmup": 4, "min_std": 1.0}},
        {"name": "warmup 1 scores from index 1",
         "args": {"series": [95.0, 96.0, 160.0, 94.0, 97.0], "alpha": 0.5, "k": 2.5, "warmup": 1, "min_std": 1.5}},
        {"name": "drop is anomalous too",
         "args": {"series": [210.0, 205.0, 214.0, 208.0, 211.0, 207.0, 212.0, 40.0, 209.0, 206.0], "alpha": 0.3, "k": 3.0, "warmup": 5, "min_std": 2.0}},
        {"name": "single point", "args": {"series": [88.0], "alpha": 0.3, "k": 3.0, "warmup": 1, "min_std": 1.0}},
        {"name": "point right after spike",
         "args": {"series": [60.0, 61.0, 59.0, 60.0, 62.0, 61.0, 60.0, 59.0, 95.0, 66.0, 61.0], "alpha": 0.4, "k": 3.0, "warmup": 6, "min_std": 1.0}},
    ]
