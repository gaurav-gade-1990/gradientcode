# Incident: floor instead of ceil put every value one bucket low, so the dashboard reported p99 about 2*alpha too optimistic and the SLO looked green during a regression.
import math


class LatencyHistogram:
    def __init__(self, alpha=0.01, max_buckets=2048):
        self.alpha = alpha
        self.max_buckets = max_buckets
        self.gamma = (1 + alpha) / (1 - alpha)
        self._log_gamma = math.log(self.gamma)
        self._counts = {}
        self._zero = 0

    def _index(self, v):
        return math.floor(math.log(v) / self._log_gamma)

    def _value(self, i):
        return 2 * self.gamma ** i / (self.gamma + 1)

    def _collapse(self):
        while len(self._counts) > self.max_buckets:
            lo, nxt = sorted(self._counts)[:2]
            self._counts[nxt] += self._counts.pop(lo)

    def record(self, value_ms, count=1):
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("count must be a positive int")
        if value_ms < 0:
            raise ValueError("negative latency")
        if value_ms == 0:
            self._zero += count
            return
        i = self._index(value_ms)
        self._counts[i] = self._counts.get(i, 0) + count
        self._collapse()

    def merge(self, other):
        if other.alpha != self.alpha:
            raise ValueError("cannot merge histograms with different alpha")
        for i, c in other._counts.items():
            self._counts[i] = self._counts.get(i, 0) + c
        self._zero += other._zero
        self._collapse()

    def quantile(self, q):
        if not 0 <= q <= 1:
            raise ValueError("q must be in [0, 1]")
        n = self.count()
        if n == 0:
            return None
        rank = q * (n - 1)
        cum = self._zero
        if cum > rank:
            return 0.0
        for i in sorted(self._counts):
            cum += self._counts[i]
            if cum > rank:
                return self._value(i)
        return self._value(max(self._counts))

    def count(self):
        return self._zero + sum(self._counts.values())

    def buckets(self):
        return [[i, self._counts[i]] for i in sorted(self._counts)]
