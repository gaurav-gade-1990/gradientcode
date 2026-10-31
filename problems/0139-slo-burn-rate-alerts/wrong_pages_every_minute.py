from collections import deque


class BurnRateAlerter:
    """No per-severity state: re-sends the page every minute the condition holds (a pager storm)."""

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
            if lb > rule["factor"] and sb > rule["factor"]:
                self.open.add(sev)
                events.append({"minute": minute, "severity": sev, "event": "open", "long_burn": lb, "short_burn": sb})
            elif sev in self.open:
                self.open.discard(sev)
                events.append({"minute": minute, "severity": sev, "event": "close", "long_burn": lb, "short_burn": sb})
        return events

    def active(self):
        return [r["severity"] for r in self.rules if r["severity"] in self.open]
