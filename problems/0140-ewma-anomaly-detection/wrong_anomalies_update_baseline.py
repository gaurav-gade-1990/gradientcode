import math


class EwmaDetector:
    """Folds every point into the baseline, so a long incident teaches the detector that incidents are normal."""

    def __init__(self, alpha, k, warmup, min_std):
        self.alpha, self.k, self.warmup, self.min_std = alpha, k, warmup, min_std
        self.mean = None
        self.var = None
        self.seen = 0

    def _learn(self, x):
        d = x - self.mean
        self.mean += self.alpha * d
        self.var = (1 - self.alpha) * (self.var + self.alpha * d * d)

    def update(self, value):
        x = float(value)
        i = self.seen
        self.seen += 1
        if i == 0:
            self.mean, self.var = x, 0.0
            return {"z": None, "anomaly": False}
        if i < self.warmup:
            self._learn(x)
            return {"z": None, "anomaly": False}
        z = (x - self.mean) / max(math.sqrt(self.var), self.min_std)
        self._learn(x)
        return {"z": z, "anomaly": abs(z) > self.k}
