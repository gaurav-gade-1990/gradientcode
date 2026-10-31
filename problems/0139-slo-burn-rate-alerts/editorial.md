## Approach

A burn rate of 1 spends the error budget exactly over the SLO period. A burn rate of 14.4 spends 2% of a 30-day budget in one hour, which is worth waking someone up for. 6 sustained over 6 hours spends 5%, which is worth a ticket.

One window is never enough. A long window alone is slow to fire and very slow to clear: after the rollback it still contains the whole incident for another hour. A short window alone fires on every blip. Requiring **both** gives you the long window's precision and the short window's fast reset.

```python
def _burn(self, window):
    recent = list(self.history)[-window:]          # last W observed minutes, fewer at startup
    req = sum(r for r, _ in recent)
    err = sum(e for _, e in recent)
    return 0.0 if req == 0 else (err / req) / self.budget

def observe(self, minute, requests, errors):
    self.history.append((requests, errors))        # deque(maxlen=longest window)
    events = []
    for rule in self.rules:
        lb, sb = self._burn(rule["long"]), self._burn(rule["short"])
        firing = lb > rule["factor"] and sb > rule["factor"]
        if firing != (rule["severity"] in self.open):   # edge-triggered
            ...toggle, append an open/close event with lb and sb...
    return events
```

The state per severity is one bit. Events are edge-triggered: the alert manager gets one `open` and one `close`, not a notification every minute.

## Common mistakes

- **Long window only.** The page stays red for most of an hour after the fix, and on-call learns to ignore it.
- **Averaging per-minute ratios.** At 3 a.m. a minute with 10 failures out of 20 requests is a 50% "outage" and pages, although it is 10 failed requests. Burn rate is a ratio of sums.
- **An off-by-one window.** `history[-(W + 1):]` silently makes every window one minute longer. The thresholds in the workbook are tuned for exact windows.
- **Level-triggered notifications.** Emitting `open` every minute the condition holds is a pager storm. Keep state and emit transitions.

## Production notes

- In Prometheus this is two recording rules per window (`sum(rate(errors[1h])) / sum(rate(requests[1h]))`) and one alert rule that ANDs the long and short ratios. Sloth and Pyrra generate exactly these rules from an SLO spec, and Datadog and Grafana SLOs ship the same multi-window logic.
- Alertmanager does the deduplication, grouping and resolve notifications; this problem's edge-triggered events are what it expects to receive.
- Low-traffic services break ratio alerts. Add a minimum request count per window, or synthesize traffic with probes, so 2 failures out of 3 requests don't page.
- For an inference API, define "bad" carefully: 5xx, timeouts, and possibly responses over the latency SLO. Pair this with `streaming-latency-percentiles` (138) for latency SLOs and with `canary-analysis` (147) to stop a rollout before it burns budget.
