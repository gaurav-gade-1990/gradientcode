## 1. What the problem is really asking

Strip away the SRE vocabulary and this is a **sliding-window ratio feeding a two-state machine**:

> each minute: append (requests, errors) to a history → for each rule, compute errors ÷ requests over its long and its short window, divided by the budget → the rule is "firing" when both are above its factor → emit an event only when firing differs from what the rule was last minute.

There are two independent pieces. The **burn rate** is a ratio of sums over the last `W` observed minutes. The **alert** is an edge-triggered flag per severity: you report transitions (`open`, `close`), not levels.

The judge's driver feeds the trace one minute at a time and records every event you return, keeping exactly the keys `minute`, `severity`, `event`, `long_burn`, `short_burn`. From those it rebuilds alert intervals (`opened`, `closed`, with `closed = None` if still open at the end), and it also calls `active()` once after the last minute. So an extra `open` event, a missing `close`, or burn values from a window that is one minute too long all fail, even if the alert is "roughly right".

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `slo` | availability target, e.g. `0.999` | the budget is `b = 1 - slo` |
| `rules` | `[{"severity", "long", "short", "factor"}]` | evaluated in this order every minute |
| `observe(minute, requests, errors)` | one call per minute, `minute = 0, 1, 2, ...` | append to history, return this minute's events |
| `active()` | called once at the end | open severities, in `rules` order |
| an event | `{"minute", "severity", "event", "long_burn", "short_burn"}` | emitted only on a transition |

The default rules are the SRE workbook pair: `page` (60-minute long window, 5-minute short window, factor 14.4) and `ticket` (360 and 30, factor 6.0). Some tests pass their own `rules` and `slo`.

Three details are easy to miss:

- **The window includes the current minute.** At minute `m`, a `W`-minute window covers `m-W+1 .. m`. That's exactly the last `W` items after you append, i.e. `history[-W:]`.
- **Early windows are partial.** Before `W` minutes have arrived, the window covers whatever has been observed. `history[-360:]` on a 93-item list gives all 93 items, which is the right behaviour for free. This is why in Example 1 the 6-hour ticket opens at minute 92.
- **Sum first, then divide.** The burn rate is `(Σ errors / Σ requests) / b`, not the mean of per-minute ratios. If the request sum is 0, the burn is `0.0`.

## 3. Trace Example 3 by hand

`slo = 0.99`, so `b = 0.01`. One rule: `page`, long 6, short 2, factor 10. Traffic is 100 requests a minute. Minutes 4 to 6 fail 28 each, the rest fail 0.

| minute | errors | long (6 min) burn | short (2 min) burn | firing? | event |
|---|---|---|---|---|---|
| 0–3 | 0 | 0.0 | 0.0 | no | - |
| 4 | 28 | 28/500/0.01 = **5.6** | 28/200/0.01 = **14.0** | no (long ≤ 10) | - |
| 5 | 28 | 56/600/0.01 = 9.33 | 56/200/0.01 = 28.0 | no (long ≤ 10) | - |
| 6 | 28 | 84/600/0.01 = **14.0** | 28.0 | **yes** | `open`, long 14, short 28 |
| 7 | 0 | 14.0 | 28/200/0.01 = 14.0 | yes | nothing (already open) |
| 8 | 0 | 14.0 | 0.0 | no | `close`, long 14, short 0 |
| 9 | 0 | 14.0 | 0.0 | no | - |

At minute 4 only 5 minutes have been observed, so the "6-minute" window divides by 500 requests, not 600. At minute 8 the long window still reads 14.0, but the short window is clean, so the page closes. That fast reset is the whole point of the second window.

The output is two events, one interval `{"opened": 6, "closed": 8}`, and `active() == []`.

### The bigger example: Example 1

2,000 requests a minute with 1 error (burn 0.5), then minutes 90–101 fail 400 a minute (burn 200), then healthy again.

| minute | 60-min burn | 5-min burn | 360-min burn | 30-min burn | event |
|---|---|---|---|---|---|
| 91 | 7.15 | 80.3 | 4.837 | 13.8 | - |
| 92 | 10.475 | 120.2 | **6.9355** | 20.45 | ticket `open` |
| 93 | 13.8 | 160.1 | 8.9894 | 27.1 | - (13.8 ≤ 14.4) |
| 94 | **17.125** | 200.0 | 11.0 | 33.75 | page `open` |
| 106 | 40.4 | **0.5** | 22.8738 | 80.3 | page `close` |
| 131 | 40.4 | 0.5 | 18.6364 | **0.5** | ticket `close` |

The ticket fires before the page because its 360-minute window is still partial: at minute 92 it averages over only 93 minutes, three of them bad. After the rollback, the page's long window still burns 40.4 at minute 106, an hour-long red alert if you used it alone. The 5-minute window clears it within five minutes.

## 4. Key idea: why two windows

A long window is **precise**: it doesn't fire on a blip, and a factor of 14.4 over an hour means 2% of a 30-day budget gone. But it is **slow to reset**: it remembers the incident for the full window. A short window resets quickly but fires on noise. Requiring *both* gets precision from the long window and fast reset from the short one. The short window can't make an alert fire on its own. It can only stop the long window from keeping it open.

The test "night traffic is not averaged per minute" shows why the ratio must be a ratio of sums. For 30 minutes the service gets 20 requests a minute, half of which fail. The 5-minute window really does burn 500 (10/20/0.001), but the 60-minute window peaks at only 3.974, because those few requests are a small fraction of the hour's traffic. Nothing fires, which is right: a few hundred failed requests at 3 a.m. aren't worth a page. If you averaged per-minute ratios, every one of those minutes would count as a 50% outage.

## 5. Key idea: edge-triggered state

Keep a set of open severities. Each minute, compute `firing` and compare it with `sev in self.open`. Emit only when they differ:

| `firing` | was open? | action |
|---|---|---|
| true | no | add to set, emit `open` |
| true | yes | nothing |
| false | yes | remove from set, emit `close` |
| false | no | nothing |

Without state, you'd send `open` every minute the condition holds. That's a pager storm, and the driver would build a new interval for each one.

## 6. Plan before you code

```
__init__: budget = 1 - slo; keep rules; history = deque(maxlen = longest window); open = empty set
_burn(W): take the last W history items; sum requests and errors; 0.0 if no requests, else ratio / budget
observe(minute, requests, errors):
    append (requests, errors)
    for each rule in order:
        lb, sb = _burn(long), _burn(short)
        firing = lb > factor and sb > factor
        if firing != (severity is open): toggle it, emit an event with lb and sb
    return the events
active(): severities in rules order that are in the open set
```

## 7. Build it one piece at a time

**Step 1: bounded history.** A `deque` with `maxlen` set to the longest window drops old minutes automatically, so memory stays at most 720 entries however long the trace runs.

```python
self.budget = 1.0 - slo
self.history = deque(maxlen=max(r["long"] for r in rules))
self.open = set()
```

**Step 2: the burn rate.** `list(self.history)[-window:]` is the last `window` minutes, or all of them early on. It's tempting to write `[-(window + 1):]` to "include the current minute", but the current minute is already the last item, because you appended it first.

```python
def _burn(self, window):
    recent = list(self.history)[-window:]
    req = sum(r for r, _ in recent)
    err = sum(e for _, e in recent)
    return 0.0 if req == 0 else (err / req) / self.budget
```

The `req == 0` guard matters in "zero-traffic minutes at start", where the first 20 minutes have no requests at all.

**Step 3: the transition.** One comparison covers all four rows of the table above. `(self.open.add if firing else self.open.discard)(sev)` picks the method and calls it; a plain `if`/`else` is equally fine.

```python
firing = lb > rule["factor"] and sb > rule["factor"]
if firing != (sev in self.open):
    ...
```

Both comparisons are strict (`>`). The tests avoid values exactly on a threshold, but the statement says strict, so match it.

**Step 4: `active()` in rules order.** A set has no order, so walk `self.rules` and keep the severities that are open.

## 8. Full solution

```python
from collections import deque  # a bounded queue that drops the oldest minute for us


# Streaming multi-window, multi-burn-rate alert evaluator.
class BurnRateAlerter:
    # Store the budget and rules, and start with no history and nothing open.
    def __init__(self, slo, rules):
        self.budget = 1.0 - slo  # the error budget: the fraction of requests allowed to fail
        self.rules = rules  # evaluated in this order every minute
        self.history = deque(maxlen=max(r["long"] for r in rules))  # only the longest window is ever needed
        self.open = set()  # severities that are currently firing

    # Burn rate over the last `window` observed minutes.
    def _burn(self, window):
        recent = list(self.history)[-window:]  # the current minute is already the last item
        req = sum(r for r, _ in recent)  # total requests in the window
        err = sum(e for _, e in recent)  # total failures in the window
        return 0.0 if req == 0 else (err / req) / self.budget  # ratio of sums, in units of the budget

    # Record one minute and return the alert transitions it causes.
    def observe(self, minute, requests, errors):
        self.history.append((requests, errors))  # record first, so every window includes this minute
        events = []  # this minute's events, in rules order
        # Each rule is evaluated independently.
        for rule in self.rules:
            sev = rule["severity"]  # the key for this rule's open/closed state
            lb, sb = self._burn(rule["long"]), self._burn(rule["short"])  # both windows' burn rates
            firing = lb > rule["factor"] and sb > rule["factor"]  # both windows must agree
            # Only a change of state is reported.
            if firing != (sev in self.open):
                (self.open.add if firing else self.open.discard)(sev)  # flip the stored state
                # Report the transition with the burn rates that caused it.
                events.append({"minute": minute, "severity": sev, "event": "open" if firing else "close",
                               "long_burn": lb, "short_burn": sb})
        return events  # often empty: nothing changed this minute

    # The severities currently open.
    def active(self):
        return [r["severity"] for r in self.rules if r["severity"] in self.open]  # rules order, not set order
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | ticket 92–131, page 94–106 | partial early windows; the short window closes the page while the long one reads 40.4 |
| Example 2 | ticket opens at 233, `closed` None, `active` `["ticket"]` | a burn of 10 never pages; an alert still open at the end |
| Example 3 | page 6–8 | exact window boundaries, and closing on the short window alone |
| night traffic is not averaged per minute | no events | ratio of sums, not mean of per-minute ratios |
| two incidents reopen the page | page 72–84 and 120–134; ticket reopens at 120 and ends open | state resets correctly, so a second incident opens a second interval |
| zero-traffic minutes at start | both open at 20 with burn 300 | the `req == 0` guard, and empty minutes adding nothing to the sums |
| flapping short window | page 3–9 and 10–12 | close and reopen on consecutive transitions, one event each |
| custom rules and slo 99.5% | slow 50–89, fast 63–77 | rules and budget come from the arguments, not hard-coded |
| sustained outage ends open | both open at 30, `active` `["page", "ticket"]` | `active()` in rules order; no repeated `open` events |
| healthy day no events | no events | burn 0.5 to 0.8 never crosses a factor |
| ticket from a long moderate burn | ticket 368–464 | a slow burn that only the 6-hour rule catches |

## 10. Complexity

Each `observe` copies the history to a list and sums up to `long` items for each rule, so it costs O(R · L) where `R` is the number of rules and `L` the longest window (≤ 720). With 800 minutes that's well under a million operations. Memory is O(L) because the deque is bounded.

In production you'd keep running sums per window instead of re-summing: add the new minute, subtract the one that falls out. That makes each update O(R). Prometheus does the equivalent with recording rules such as `sum(rate(errors[1h])) / sum(rate(requests[1h]))`, evaluated every 30 to 60 seconds.

## 11. If you got Wrong Answer

- **The page never closes in Example 3 (`closed` None, `active` `["page"]`), and in Example 1 both alerts stay open.** You check only the long window. Require the short window too.
- **`long_burn` at minute 6 of Example 3 is 12 instead of 14, and the close at minute 8 shows `short_burn` 9.33 instead of 0.** Your windows are one minute too long, from `history[-(window + 1):]`.
- **Example 3 has an extra `open` at minute 7 and the first interval never closes.** You emit `open` every minute the condition holds. Compare with the stored state.
- **"night traffic is not averaged per minute" fires a ticket at minute 60 and a page at minute 61.** You average per-minute ratios. Sum errors and requests over the window, then divide.
- **Runtime Error in "zero-traffic minutes at start".** Division by zero: return `0.0` when the window has no requests.
- **`active` in "sustained outage ends open" is `["ticket", "page"]` on some runs and right on others.** You returned `list(self.open)`. String hashing is randomized per process, so a set's order changes from run to run. Walk `rules` instead.

## 12. Follow-ups an interviewer might ask

- *How do you handle low-traffic services?* Ratio alerts are noisy when there are few requests. Add a minimum request count per window before a rule can fire, or send synthetic probe traffic so the denominator is never tiny.
- *How would you alert on latency, not errors?* Define a "bad" request as one slower than the latency SLO, count those as errors, and the same burn-rate math applies. You need a streaming percentile or a histogram to compute it (problem 138, streaming-latency-percentiles).
- *Why 14.4 and 6?* With a 30-day budget, burning at 14.4 for one hour spends 2% of it (14.4 × 1 / 720), and 6 for six hours spends 5%. The factors are chosen from how much budget you're willing to lose before someone acts.
- *How would you make `observe` O(1) per rule?* Keep a running sum of requests and errors per window, and subtract the minute that leaves the window. With a shared deque, the leaving minute is at index `-W-1` before you append.
- *How does this connect to deployments?* Burn-rate checks can gate a rollout: a canary that burns budget faster than the baseline gets rolled back before it reaches everyone (problem 147, canary-analysis).
