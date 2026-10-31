# Bug: active() returns list(self.open), the set's iteration order, instead of rules order.
# String hashing is randomized per process, so the order changes from run to run.
from collections import deque


class BurnRateAlerter:
    def __init__(self, slo, rules):
        self.budget = 1.0 - slo
        self.rules = rules
        self.history = deque(maxlen=max(r["long"] for r in rules))
        self.open = set()

    def _burn(self, window):
        recent = list(self.history)[-window:]
        req = sum(r for r, _ in recent)
        err = sum(e for _, e in recent)
        return 0.0 if req == 0 else (err / req) / self.budget

    def observe(self, minute, requests, errors):
        self.history.append((requests, errors))
        events = []
        for rule in self.rules:
            sev = rule["severity"]
            lb, sb = self._burn(rule["long"]), self._burn(rule["short"])
            firing = lb > rule["factor"] and sb > rule["factor"]
            if firing != (sev in self.open):
                (self.open.add if firing else self.open.discard)(sev)
                events.append({"minute": minute, "severity": sev, "event": "open" if firing else "close",
                               "long_burn": lb, "short_burn": sb})
        return events

    def active(self):
        return list(self.open)
