## 1. What the problem is really asking

When a provider is down, every request sent to it waits out a timeout and then fails. Retries make it worse (problem 124). A circuit breaker notices the outage and **fails fast**: for a while, it rejects requests without sending them at all. Later it lets a few **probes** through, and only when they succeed does it send full traffic again.

Under the story, this is **a three-state machine with a rolling error rate**:

```
closed    --(error rate >= threshold, with at least min_calls outcomes)--> open
open      --(open_timeout_s has passed, noticed in allow())--------------> half_open
half_open --(any probe fails)--------------------------------------------> open
half_open --(half_open_probes probes succeed)----------------------------> closed
```

The part most hand-written breakers get wrong is **concurrency**. A slow call admitted while the breaker was closed can finish after it has opened, or while it's half-open. That result belongs to a state that no longer exists, and it must be ignored. The problem gives you the tool for this: every state change starts a new **generation**, and a permit remembers the generation it was issued in.

The judge replays a trace of concurrent calls, reads `state` after every `allow()` and `record()`, and grades each call's decision (`allowed` or `rejected`), the full timeline of transitions `[t, from, to]`, and the final state.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `clock` | a `gc_runtime.Clock` | `clock.now()` in `allow` and `record` |
| `window_s` | length of the rolling window | drop outcomes with `t <= now - window_s` |
| `failure_rate` | trip threshold, e.g. 0.5 | trip when `failures / count >= failure_rate` |
| `min_calls` | outcomes needed before a rate means anything | no trip below it |
| `open_timeout_s` | how long to stay open | half-open once `now >= opened_at + open_timeout_s` |
| `half_open_probes` | probes allowed per half-open period | also the successes needed to close |
| `allow()` | before each request | returns a permit, or `None` to reject |
| `record(permit, ok)` | when an admitted request finishes | updates the state, unless the permit is stale |

Three details are easy to miss:

- **The two boundaries differ.** The window drops outcomes at exactly `now - window_s` (exclusive). The open timeout ends at exactly `opened_at + open_timeout_s` (inclusive).
- **open → half_open happens inside `allow()`.** There's no timer. The first request after the timeout moves the state and becomes the first probe.
- **Entering any state clears the window and counters.** The window only holds outcomes from the current closed period.

## 3. Trace the examples by hand

The tests use `window_s=10`, `failure_rate=0.5`, `min_calls=4`, `open_timeout_s=5`, `half_open_probes=2`.

**Example 1.** Each call takes 0.5 s.

| t | event | window after | rate | state |
|---|---|---|---|---|
| 0.5 | c1 ok | 1 ok | 0/1 | closed |
| 1.5 | c2 fail | 1 ok, 1 fail | 1/2, but 2 < 4 calls | closed |
| 2.5 | c3 fail | 1 ok, 2 fail | 2/3, but 3 < 4 | closed |
| 3.5 | c4 fail | 1 ok, 3 fail | 3/4 = 0.75 ≥ 0.5, 4 calls | **open**, `opened_at=3.5` |
| 4 | c5 `allow()` | | 4 < 3.5 + 5 | rejected |
| 8 | c6 `allow()` | | 8 < 8.5 | rejected |

Timeline: `[[3.5, 'closed', 'open']]`.

**Example 2** is the recovery path. Four failures at t=0 trip the breaker at 0.5. Then:

| t | event | state | probes issued | successes |
|---|---|---|---|---|
| 6 | p1 `allow()`: 6 ≥ 5.5, so enter half_open and issue probe 1 | half_open | 1 | 0 |
| 6.25 | p2 `allow()`: probe 2 | half_open | 2 | 0 |
| 6.5 | p3 `allow()`: both probes out | rejected | 2 | 0 |
| 7 | p1 succeeds | half_open | 2 | 1 |
| 7.25 | p2 succeeds; 2 = `half_open_probes` | **closed** | | |
| 8 | c8 `allow()` | allowed | | |

**Example 3** is the stale result. `slow` is admitted at t=0 (generation 1, closed) and takes 9 s. Four failures trip the breaker at 0.5 (generation 2, open). p1 at t=7 moves it to half_open (generation 3), and p1 fails at 7.5, so it's open again (generation 4). When `slow` finishes at 9.0, its permit says generation 1, the breaker is on generation 4, and the success is ignored. c7 at t=8 is rejected, and the breaker stays open.

## 4. Key idea: generations make stale results a single comparison

Every `_enter(state)` bumps `self.generation`, and `allow()` returns the current generation as the permit. Then `record` starts with:

```python
if permit != self.generation:
    return
```

"stale failure must not reopen" shows what goes wrong without it. `slowfail` is admitted at t=0 and fails at t=6.0, by which time the breaker has tripped (0.5) and gone half-open (5.5), with two probes in flight. If its failure counted, the half-open breaker would reopen at 6.0 because of a call that was sent before the outage was even detected. With the check, the probes succeed at 7.5 and 7.75 and the breaker closes.

The permit only has to be non-`None`, so the generation number itself is a perfect permit.

## 5. Key idea: a rate needs a denominator and a window

`min_calls` stops the breaker from tripping on noise. In "below min_calls never trips", three failures in a row give a 100% failure rate, but with 3 < 4 outcomes the breaker stays closed. Without the guard, one failure out of one call during a quiet hour takes the provider out of rotation for everyone.

The window stops it from tripping on old history. In "rolling window forgets old failures", calls alternate fail and ok every 4 seconds. A 10-second window holds about three outcomes, which is below `min_calls`, until `h` (fail at 28.5) and `i` (ok at 29.5) arrive close together. At 29.5 the window holds `f, g, h, i` (fail, ok, fail, ok): 2/4 = 0.5, so it trips. A cumulative count since process start would have tripped much earlier.

## 6. Plan before you code

```
_enter(state): state = s; generation += 1; clear window, issued, successes;
               if open: opened_at = now
allow():
    if open:  timeout not passed -> None; else _enter(half_open)
    if half_open: issued >= probes -> None; else issued += 1
    return generation
record(permit, ok):
    stale permit -> ignore
    closed:    append (now, ok); prune t <= now - window_s;
               count >= min_calls and fails/count >= rate -> _enter(open)
    half_open: fail -> _enter(open); success -> successes += 1; enough -> _enter(closed)
```

The open branch falls through to the half_open branch on purpose. The request that notices the timeout is the first probe, so it has to go through the probe counter.

## 7. Build it one piece at a time

**Step 1: one place for transitions.** Every transition goes through `_enter`, so the generation bump and the resets can't be forgotten. `__init__` calls it too, so the breaker starts closed on generation 1.

```python
    def _enter(self, state):
        self.state = state
        self.generation += 1
        self.window = []
        self.issued = 0
        self.successes = 0
        if state == "open":
            self.opened_at = self.clock.now()
```

**Step 2: `allow()`.** The `<` makes the timeout inclusive at its end. In "open timeout boundary is inclusive", the breaker opens at 1.0, `e` at 5.75 is rejected, and `f` at exactly 6.0 becomes the first probe.

```python
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
```

**Step 3: `record()` while closed.** Append first, then prune, then test. The `>` keeps only outcomes strictly newer than `now - window_s`. In "window boundary is exclusive", the failure at t=0 is dropped exactly at t=10, so the window never reaches four outcomes.

```python
        if self.state == "closed":
            self.window.append((now, ok))
            self.window = [(t, o) for t, o in self.window if t > now - self.window_s]
            fails = sum(1 for _, o in self.window if not o)
            if len(self.window) >= self.min_calls and fails / len(self.window) >= self.failure_rate:
                self._enter("open")
```

**Step 4: `record()` while half-open.** One failure is enough to reopen, because a probe is a test of whether the provider is back. Closing takes `half_open_probes` successes.

```python
        elif self.state == "half_open":
            if not ok:
                self._enter("open")
            else:
                self.successes += 1
                if self.successes >= self.half_open_probes:
                    self._enter("closed")
```

## 8. Full solution

```python
class CircuitBreaker:  # fail fast while a provider is down, probe carefully when it returns
    def __init__(self, clock, window_s=60.0, failure_rate=0.5, min_calls=5, open_timeout_s=30.0, half_open_probes=2):  # config
        self.clock = clock  # the only source of time
        self.window_s = window_s  # how far back the error rate looks
        self.failure_rate = failure_rate  # trip threshold
        self.min_calls = min_calls  # outcomes needed before the rate means anything
        self.open_timeout_s = open_timeout_s  # how long to fail fast before probing
        self.half_open_probes = half_open_probes  # probes per half-open period, and successes needed to close
        self.generation = 0  # bumped on every state change; permits carry it
        self._enter("closed")  # start closed, on generation 1

    def _enter(self, state):  # the only way to change state, so nothing is forgotten
        self.state = state  # the judge reads this after every call
        self.generation += 1  # results from before this change become stale
        self.window = []          # (t, ok) outcomes while closed
        self.issued = 0           # probes handed out while half-open
        self.successes = 0  # probe successes while half-open
        if state == "open":  # remember when we tripped
            self.opened_at = self.clock.now()  # the timeout counts from here

    def allow(self):  # called before each request: a permit, or None to fail fast
        now = self.clock.now()  # current virtual time
        if self.state == "open":  # failing fast
            if now < self.opened_at + self.open_timeout_s:  # timeout not over yet (inclusive at the end)
                return None  # reject without touching the provider
            self._enter("half_open")  # lazily: the first request after the timeout becomes a probe
        if self.state == "half_open":  # only a few probes may go through
            if self.issued >= self.half_open_probes:  # all probes are already out
                return None  # everyone else waits, to avoid a thundering herd
            self.issued += 1  # hand out one more probe
        return self.generation  # the permit: which generation this request belongs to

    def record(self, permit, ok):  # an admitted request finished
        if permit != self.generation:  # it was admitted before the last state change
            return                # stale: issued before the last state change
        now = self.clock.now()  # completion time
        if self.state == "closed":  # normal traffic: track the error rate
            self.window.append((now, ok))  # add this outcome first
            self.window = [(t, o) for t, o in self.window if t > now - self.window_s]  # keep only the window
            fails = sum(1 for _, o in self.window if not o)  # failures still in the window
            # trip only with enough data and a high enough failure rate
            if len(self.window) >= self.min_calls and fails / len(self.window) >= self.failure_rate:
                self._enter("open")  # start failing fast
        elif self.state == "half_open":  # this was a probe
            if not ok:  # the provider still isn't healthy
                self._enter("open")  # back to failing fast, with a fresh timeout
            else:  # one good probe
                self.successes += 1  # count it
                if self.successes >= self.half_open_probes:  # every probe succeeded
                    self._enter("closed")  # send full traffic again
```

## 9. How the test cases map to the code

| test case | expected timeline | what it checks |
|---|---|---|
| Example 1 | open at 3.5; c5 and c6 rejected | `min_calls` delays the trip; the open timeout |
| Example 2 | open 0.5, half_open 6.0, closed 7.25 | lazy half-open; the probe limit; closing after two successes |
| Example 3 | open 0.5, half_open 7.0, open 7.5 | a failed probe reopens; the slow success at 9.0 doesn't close it |
| stale success must not close a half-open breaker | open 0.5, half_open 6.0, closed 9.0; c8 rejected | the breaker closes on the probes' results |
| stale failure must not reopen | open 0.5, half_open 5.5, closed 7.75 | the generation check: `slowfail` at 6.0 is ignored |
| probe limit under concurrency | closed at 8.2; h3 and h4 rejected | `half_open_probes=3` under concurrent requests |
| rolling window forgets old failures | open at 29.5 | pruning by time |
| window boundary is exclusive | never trips | `t > now - window_s` |
| below min_calls never trips | never trips | three failures out of three is not enough |
| open timeout boundary is inclusive | half_open at exactly 6.0 | `now < opened_at + timeout` rejects; equality probes |
| min_calls 1 and failure_rate 1 | never trips | 1 failure out of 2 is 0.5, not 1.0 |
| reopen then recover twice | 8 transitions, final closed | repeated cycles; each `_enter` resets counters |
| outage trace | 9 transitions over a simulated outage; 62 allowed, 28 rejected | everything together |

In Example 3 and "stale success must not close a half-open breaker", removing the generation check doesn't change the result. In Example 3 the breaker is open when the stale success lands, and `record` ignores outcomes while open anyway. In the other case, the stale success at 6.5 and probe p1 at 9.0 reach two successes at the same moment the two probes would. "stale failure must not reopen" is the case that catches a missing check.

## 10. Complexity

`allow()` is O(1). `record()` while closed is O(W), where W is the number of outcomes in the window, because it rebuilds the list on every call. With a high request rate that's wasteful; a `deque` with `popleft` while the oldest entry is too old, plus running counts of outcomes and failures, makes it O(1) amortized. Resilience4j uses a ring buffer of per-second buckets for the same reason.

In production you keep **one breaker per (provider, model, region)**, so an outage of one model doesn't stop traffic to healthy ones, and each gateway replica usually keeps its own breaker: a breaker is a local health signal, and sharing one through Redis adds a dependency that can itself fail.

## 11. If you got Wrong Answer

- **Example 1 trips at 1.5.** You're missing `min_calls`. One failure out of two calls isn't enough data.
- **"rolling window forgets old failures" trips early.** You never prune the window.
- **"window boundary is exclusive" trips at t=10.** Your prune keeps `t >= now - window_s`. Use `>`.
- **Example 2's p3 is allowed.** Half-open doesn't limit probes. Count `issued`.
- **"stale failure must not reopen" reopens at 6.0.** You're counting stale results. Compare the permit with the current generation.
- **"open timeout boundary is inclusive" rejects `f` at 6.0.** Your timeout test is `<=`. Half-open starts at exactly `opened_at + open_timeout_s`.
- **Example 2 reopens at 8.5, right after closing.** `_enter` doesn't clear the window, so the four failures from t=0.5 are still in it when c8 succeeds. Reset the window and counters on every transition.

## 12. Follow-ups an interviewer might ask

- *What should count as a failure?* 5xx, timeouts and connection errors. Not 400s, which are your bug. A 429 usually means "slow down" rather than "down", so many teams track it on a separate breaker or let the rate limiter handle it (problem 123, token-bucket-rate-limiter).
- *What about a provider that answers, but in 40 seconds?* Add a slow-call rate: calls over a latency threshold count as failures. For a chat UI, that slow provider is effectively down.
- *What does the gateway do while the breaker is open?* Fail over to another provider or model, and hedge slow calls (problem 134, gateway-failover-hedging). The router can also read breaker state to stop sending traffic to a degraded model (problem 126, model-router).
- *How do retries and the breaker interact?* The breaker goes in front of the retry loop. Once it opens, retries fail fast instead of piling onto the outage (problem 124, retry-with-backoff).
- *Why lazy half-open instead of a timer?* No background thread, no timer to cancel, and the transition happens exactly when there's a request to use as a probe. Resilience4j and most gateways do it this way by default.
