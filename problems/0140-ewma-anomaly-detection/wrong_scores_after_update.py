import math


class EwmaDetector:
    """Updates the baseline with the point, then scores it: the spike drags the mean toward itself and hides."""

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
        old = (self.mean, self.var)
        self._learn(x)
        if i < self.warmup:
            return {"z": None, "anomaly": False}
        z = (x - self.mean) / max(math.sqrt(self.var), self.min_std)
        anomaly = abs(z) > self.k
        if anomaly:
            self.mean, self.var = old
        return {"z": z, "anomaly": anomaly}
