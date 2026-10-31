# Incident: the first 5xx after a deploy tripped the breaker on 1 of 1 calls and took the
# provider out of rotation for every tenant during a quiet hour.
class CircuitBreaker:
    def __init__(self, clock, window_s=60.0, failure_rate=0.5, min_calls=5, open_timeout_s=30.0, half_open_probes=2):
        self.clock = clock
        self.window_s = window_s
        self.failure_rate = failure_rate
        self.min_calls = min_calls
        self.open_timeout_s = open_timeout_s
        self.half_open_probes = half_open_probes
        self.generation = 0
        self._enter("closed")

    def _enter(self, state):
        self.state = state
        self.generation += 1
        self.window = []          # (t, ok) outcomes while closed
        self.issued = 0           # probes handed out while half-open
        self.successes = 0
        if state == "open":
            self.opened_at = self.clock.now()

    def allow(self):
        now = self.clock.now()
        if self.state == "open":
            if now < self.opened_at + self.open_timeout_s:
                return None
            self._enter("half_open")
        if self.state == "half_open":
            if self.issued >= self.half_open_probes:
                return None
            self.issued += 1
        return self.generation

    def record(self, permit, ok):
        if permit != self.generation:
            return                # stale: issued before the last state change
        now = self.clock.now()
        if self.state == "closed":
            self.window.append((now, ok))
            self.window = [(t, o) for t, o in self.window if t > now - self.window_s]
            fails = sum(1 for _, o in self.window if not o)
            if fails / len(self.window) >= self.failure_rate:
                self._enter("open")
        elif self.state == "half_open":
            if not ok:
                self._enter("open")
            else:
                self.successes += 1
                if self.successes >= self.half_open_probes:
                    self._enter("closed")
