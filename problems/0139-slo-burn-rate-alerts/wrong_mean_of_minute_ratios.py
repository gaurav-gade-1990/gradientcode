from collections import deque


class BurnRateAlerter:
    """Averages each minute's error ratio, so 10 failures out of 20 night requests look like a 50% outage."""

    def __init__(self, slo, rules):
        self.budget = 1.0 - slo
        self.rules = rules
        self.history = deque(maxlen=max(r["long"] for r in rules))
        self.open = set()

    def _burn(self, window):
        ratios = [e / r for r, e in list(self.history)[-window:] if r > 0]
        return 0.0 if not ratios else (sum(ratios) / len(ratios)) / self.budget

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
        return [r["severity"] for r in self.rules if r["severity"] in self.open]
