Last week your primary model provider returned 5xx for 20 minutes, and every agent kept sending it traffic and waiting out timeouts. Put a circuit breaker in front of the provider so that the gateway fails fast while the provider is down, and probes it carefully when it comes back.

Implement `class CircuitBreaker`:

- `CircuitBreaker(clock, window_s=60.0, failure_rate=0.5, min_calls=5, open_timeout_s=30.0, half_open_probes=2)`, where `clock` is a `gc_runtime.Clock`.
- `state`: an attribute, one of `"closed"`, `"open"` or `"half_open"`. It starts `"closed"`.
- `allow()`: called before each request. Return `None` to reject the request (fail fast), or any non-`None` **permit** to let it through.
- `record(permit, ok)`: called when an admitted request finishes, with the permit `allow()` returned and `ok=True` for success or `False` for failure.

Every change of state starts a new **generation**. A permit belongs to the generation it was issued in, and `record` silently ignores a permit from an earlier generation (a stale result). Requests are concurrent, so a slow call admitted while closed can finish after the breaker has opened.

| state | `allow()` | `record(permit, ok)` with a current permit |
|---|---|---|
| `closed` | return a permit | Append `(now, ok)` to the window, then drop every outcome with time `<= now - window_s`. If the window holds `>= min_calls` outcomes and `failures / count >= failure_rate`, go to `open`. |
| `open` | If `now >= opened_at + open_timeout_s`, go to `half_open` and answer as `half_open` does. Otherwise return `None`. | none can be current: no permits are issued while open |
| `half_open` | If fewer than `half_open_probes` permits have been issued in this generation, issue one. Otherwise return `None`. | A failure goes back to `open` (with `opened_at = now`). A success is counted, and when the count reaches `half_open_probes`, go to `closed`. |

Entering `open` records `opened_at = now`. Entering any state clears the outcome window, the probe count and the success count. State changes happen only inside `allow()` and `record()`.

The judge replays a trace of calls. Each call starts at `t`, asks `allow()`, and if admitted finishes at `t + latency` with a scripted result. Completions at a given instant are processed before calls that start at the same instant, and simultaneous completions run in the order their calls started. The judge reads `state` after every `allow()` and `record()` and grades each call's decision plus the full timeline of transitions `[t, from, to]`.

**Constraints**

- `0 < failure_rate <= 1`, `min_calls >= 1`, `half_open_probes >= 1`
- At most 200 calls; times are in seconds and never decrease
- Use only `clock.now()` for time
