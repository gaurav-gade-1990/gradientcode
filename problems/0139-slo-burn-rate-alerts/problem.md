Your checkout API has a 99.9% availability SLO, and on-call is tired of alerts that fire on one bad minute and then stay red for an hour after the fix. Implement the multi-window, multi-burn-rate alerting from the Google SRE workbook as a streaming evaluator.

```python
class BurnRateAlerter:
    def __init__(self, slo, rules): ...
    def observe(self, minute, requests, errors) -> list: ...
    def active(self) -> list: ...
```

- `slo` is the availability target, e.g. `0.999`. The error budget is $b = 1 - \text{slo}$.
- `rules` is a list of dicts `{"severity": str, "long": int, "short": int, "factor": float}`. Windows are in minutes. The judge's default is the workbook pair: `page` with `long=60, short=5, factor=14.4`, and `ticket` with `long=360, short=30, factor=6.0`. Severities are distinct.
- `observe` is called once per minute with `minute = 0, 1, 2, ...` (consecutive), the number of requests served in that minute, and how many of them failed. It returns the list of events emitted at that minute (often empty).
- `active()` returns the severities that are currently open, in `rules` order.

**Burn rate.** At minute $m$, the burn rate over a window of $W$ minutes is

$$
\text{burn}_W(m) = \frac{1}{b}\cdot\frac{\sum_{t=m-W+1}^{m} \text{errors}_t}{\sum_{t=m-W+1}^{m} \text{requests}_t}
$$

Only observed minutes count, so before $W$ minutes have arrived the window covers minutes $0..m$. If the window's request sum is 0, its burn rate is `0.0`. Sum first, then divide: a quiet minute with 1 failure out of 2 requests must not weigh the same as a busy minute.

**Rules.** After recording the minute, evaluate each rule in `rules` order:

| condition | rule state | emit |
|---|---|---|
| `burn_long > factor` and `burn_short > factor` (both strict) | closed | an `open` event, rule becomes open |
| same condition true | open | nothing |
| condition false | open | a `close` event, rule becomes closed |
| condition false | closed | nothing |

Each event is a dict with exactly these keys:

```python
{"minute": m, "severity": "page", "event": "open", "long_burn": 31.2, "short_burn": 200.0}
```

`long_burn` and `short_burn` are the two burn rates for that rule at that minute. Events from one minute are returned in `rules` order.

The judge feeds a traffic trace one minute at a time and grades every event you emit, the alert intervals derived from them (`closed` is `None` if the alert is still open at the end), and `active()` after the last minute.

**Constraints**

- `0.9 <= slo < 1`, `1 <= short <= long <= 720`
- Up to 800 minutes per trace; `0 <= errors <= requests <= 10**6`
- Burn rates are compared with relative tolerance `1e-6`; the tests avoid values that sit exactly on a threshold.
