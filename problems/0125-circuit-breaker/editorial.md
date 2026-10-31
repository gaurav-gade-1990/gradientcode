## Approach

A circuit breaker is a three-state machine around a rolling error rate.

```
closed --(rate >= threshold, count >= min_calls)--> open
open   --(open_timeout elapsed, on next allow())--> half_open
half_open --(any probe fails)--> open
half_open --(half_open_probes successes)--> closed
```

```python
def allow(self):
    if self.state == "open":
        if now < self.opened_at + self.open_timeout_s:
            return None                       # fail fast
        self._enter("half_open")
    if self.state == "half_open":
        if self.issued >= self.half_open_probes:
            return None                       # probes are out; everyone else waits
        self.issued += 1
    return self.generation                    # the permit

def record(self, permit, ok):
    if permit != self.generation:
        return                                # stale result from before a transition
    ...
```

`_enter(state)` bumps the generation and clears the window and counters. The generation is the piece most hand-rolled breakers miss. Calls are concurrent, so a result can arrive after the state it was admitted under has gone. Tagging each permit with the generation makes "which state does this result belong to?" a single comparison.

**Rolling window plus `min_calls`.** A rate needs a denominator. With one call in the window, one failure is a 100% failure rate. `min_calls` stops the breaker from tripping on noise during quiet periods, and the window stops it from tripping on errors that happened long ago.

## Common mistakes

- **No `min_calls`.** The first error at 3 a.m. trips the breaker.
- **Counting stale results.** A slow success from before the trip closes a half-open breaker while the provider is still down.
- **Unlimited half-open traffic.** Letting the whole backlog through at once is a thundering herd that knocks the recovering provider over again.
- **Cumulative counters.** Without pruning, a long-lived pod collects enough rare failures to trip on a healthy provider.
- **A background timer for open to half_open.** Doing it lazily in `allow()` needs no thread and is what Resilience4j and most gateways do by default.

## Production notes

- Resilience4j (`slidingWindowType`, `minimumNumberOfCalls`, `failureRateThreshold`, `waitDurationInOpenState`, `permittedNumberOfCallsInHalfOpenState`) has exactly these parameters. Envoy's outlier detection is the per-host version: it ejects a host after consecutive 5xx and brings it back after a base ejection time.
- Decide what counts as a failure. 5xx, timeouts and connection errors should count. A 400 is your bug, not the provider's, and a 429 usually means "slow down" (problem 123) rather than "down", so many teams track 429s on a separate breaker or not at all.
- Keep one breaker per (provider, model, region), not one global breaker, so that an outage of one model doesn't fail over traffic that was healthy.
- Most teams add a slow-call rate as well: calls over a latency threshold count as failures, because a provider that answers in 40 s is effectively down for a chat UI.
- The breaker's open state is what the failover gateway (problem 134) checks before it sends or hedges. Pair it with retries (problem 124), so that retries stop as soon as the breaker opens instead of piling onto the outage.
