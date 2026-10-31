## 1. What the problem is really asking

Model providers fail in ordinary ways: a 429 when you're over your rate limit, a 503 during a deploy, a timeout under load. Most of these go away if you wait and try again. Some don't: a 400 for a malformed request fails the same way every time. A retry wrapper answers three questions:

- **Whether** to retry: only errors that a later attempt could fix.
- **How long** to wait: exponential backoff, capped, with full jitter, and never less than the server's `retry_after`.
- **When** to give up: after `max_attempts` total calls, raising the last error.

Under the story, this is **a bounded loop with a `try`/`except` and one formula**. The judge doesn't just check what you return. It records how many times `fn` was called, every `clock.sleep` with its exact duration, how many times you called `rand()`, and the final virtual time. So an extra sleep, a missed `rand()` call, or one retry too many is a Wrong Answer even if the outcome is right.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `fn` | one model call; returns a result or raises | `return fn()` inside a `try` |
| `clock` | a `gc_runtime.Clock` | `clock.sleep(seconds)` advances virtual time and records the sleep |
| `rand` | returns the next jitter draw in `[0, 1)` | exactly once per retry |
| `max_attempts` | total calls to `fn`, not retries | the loop bound |
| `base`, `cap` | backoff parameters in seconds | `min(cap, base * 2**k)` |

| error | retry? |
|---|---|
| `RateLimitError` (429) | yes, and respect `retry_after` |
| `ServerError` (5xx) | yes |
| `TimeoutError_` | yes |
| `BadRequestError` (400), anything else | no, re-raise now |

Three details are easy to miss:

- **`TimeoutError_` has a trailing underscore.** It's `gc_runtime`'s class, not Python's built-in `TimeoutError`. Catching the built-in misses it, and Example 1's timeout escapes as an error.
- **`k` counts retries from 0.** The first sleep uses `base * 2**0 = base`.
- **No sleep after the last failure.** When attempt `max_attempts` fails, raise immediately. Sleeping first only adds latency.

## 3. Trace the examples by hand

The driver's fake model takes 0.25 s of virtual time per call. The jitter draws are `[0.5, 0.25, 0.9, 0.1, 0.6, ...]`.

**Example 1.** The script is server error, timeout, success. Defaults: `base=0.5`, `cap=8.0`.

| attempt | `fn()` | k | `rand()` | backoff = min(8, 0.5·2^k) | sleep | clock after |
|---|---|---|---|---|---|---|
| 0 | `ServerError` | 0 | 0.5 | 0.5 | 0.25 | 0.5 |
| 1 | `TimeoutError_` | 1 | 0.25 | 1.0 | 0.25 | 1.0 |
| 2 | success | | | | | 1.25 |

Output: `calls: 3`, `sleeps: [0.25, 0.25]`, `rand_calls: 2`, `t: 1.25`.

**Example 2.** A 429 with `retry_after=3.0`, then success. Jitter gives 0.5 × 0.5 = 0.25, but the server asked for 3 seconds, so sleep `max(0.25, 3.0) = 3.0`. `rand()` was still called once. `t` is 0.25 + 3.0 + 0.25 = 3.5.

**Example 3.** A 400. No retry, no sleep, no `rand()`: `raised: 'BadRequestError'`, `calls: 1`.

**The trickiest hidden case, "exhausted".** Five 429s with no `retry_after`, then a success that is never reached:

| attempt | k | `rand()` | backoff | sleep |
|---|---|---|---|---|
| 0 | 0 | 0.5 | 0.5 | 0.25 |
| 1 | 1 | 0.25 | 1.0 | 0.25 |
| 2 | 2 | 0.9 | 2.0 | 1.8 |
| 3 | 3 | 0.1 | 4.0 | 0.4 |
| 4 | | | | none: last attempt, raise |

`calls: 5`, four sleeps, `rand_calls: 4`, and the raised error is `RateLimitError`.

## 4. Key idea: why full jitter

Suppose the provider hiccups and 1,000 agents all fail at the same moment. With plain exponential backoff, they all retry at exactly 0.5 s, then all at 1.5 s, in synchronized waves that keep knocking the provider over. Full jitter draws each delay uniformly from `[0, backoff]`, which spreads the retries across the whole window. AWS's analysis of backoff variants found full jitter does the least total work.

The `cap` stops the backoff from growing without bound. In "cap reached" (`base=1.0`, `cap=4.0`, every draw 0.99), the sleeps are `0.99, 1.98, 3.96, 3.96, 3.96, 3.96`: the backoff doubles to 4 and stays there. Without the cap the fourth sleep would be 0.99 × 8.

## 5. Key idea: `retry_after` is a floor, and `rand()` still runs

The server knows its own recovery time. Retrying sooner just earns another 429. So `retry_after` is a **lower bound** on the delay: take `max(delay, retry_after)`. It isn't a replacement. In "retry_after smaller than jitter" the server asks for 0.01 s, the jitter is 0.9 × 2.0 = 1.8, and you sleep 1.8.

Call `rand()` every retry, even when `retry_after` wins. The draws are a sequence; skipping one shifts every later delay. In "retry_after zero", the first retry draws 0.5 (delay 0.25, `retry_after` 0.0, sleep 0.25) and the second draws 0.25 (delay 0.25, `retry_after` 1.5, sleep 1.5). `rand_calls` is 2.

## 6. Plan before you code

```
for attempt in 0 .. max_attempts-1:
    try: return fn()
    except retryable error e:
        if this was the last attempt: re-raise e
        delay = rand() * min(cap, base * 2**attempt)
        if e is a RateLimitError with retry_after: delay = max(delay, retry_after)
        clock.sleep(delay)
    (any other error propagates on its own)
```

The loop index doubles as `k`: attempt 0 failing leads to retry 0.

## 7. Build it one piece at a time

**Step 1: the retryable set.** A tuple of classes works directly in `except`. Anything not in it, including `BadRequestError`, isn't caught, so it propagates with no extra code.

```python
from gc_runtime import RateLimitError, ServerError, TimeoutError_

RETRYABLE = (RateLimitError, ServerError, TimeoutError_)
```

**Step 2: the loop, and giving up.** On the last attempt, a bare `raise` re-raises the current exception with its traceback, before any sleep.

```python
    for attempt in range(max_attempts):
        try:
            return fn()
        except RETRYABLE as e:
            if attempt == max_attempts - 1:
                raise
```

With `max_attempts=1` ("single attempt"), the first failure is already the last attempt: one call, no sleep.

**Step 3: the delay.** `rand()` first, every time; then the `retry_after` floor. Check `is not None` rather than truthiness, so a `retry_after` of `0.0` is handled by the same code path.

```python
            delay = rand() * min(cap, base * 2 ** attempt)
            if isinstance(e, RateLimitError) and e.retry_after is not None:
                delay = max(delay, e.retry_after)
            clock.sleep(delay)
```

## 8. Full solution

```python
from gc_runtime import RateLimitError, ServerError, TimeoutError_  # the simulated transient failures

RETRYABLE = (RateLimitError, ServerError, TimeoutError_)  # errors a later attempt could fix; 400s aren't here


def call_with_retry(fn, clock, rand, max_attempts=5, base=0.5, cap=8.0):  # one model call with retries
    for attempt in range(max_attempts):  # max_attempts total calls; attempt is also the backoff exponent k
        try:  # try the call
            return fn()  # success ends everything
        except RETRYABLE as e:  # transient: worth another try (anything else propagates untouched)
            if attempt == max_attempts - 1:  # that was the last allowed call
                raise  # give up with the last error, without a pointless final sleep
            delay = rand() * min(cap, base * 2 ** attempt)  # full jitter over a capped exponential backoff
            if isinstance(e, RateLimitError) and e.retry_after is not None:  # the server said how long
                delay = max(delay, e.retry_after)  # never retry sooner than it asked
            clock.sleep(delay)  # virtual sleep; the judge records it
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | success; sleeps `[0.25, 0.25]`; 3 calls | 5xx and timeout are retried; `2**k` backoff with jitter |
| Example 2 | success; sleeps `[3]` | `retry_after` beats a smaller jitter |
| Example 3 | `BadRequestError`; 1 call; no sleeps | 400 isn't retried |
| success first try | 1 call, no sleeps, no `rand()` | the fast path |
| exhausted | `RateLimitError`; 5 calls; sleeps `[0.25, 0.25, 1.8, 0.4]` | the attempt limit; no sleep after the last failure |
| exhausted max_attempts=2 | `ServerError`; 2 calls; sleeps `[0.25]` | a custom limit |
| cap reached | sleeps `[0.99, 1.98, 3.96, 3.96, 3.96, 3.96]` | `min(cap, ...)` |
| retry_after smaller than jitter | sleeps `[1.8]` | `retry_after` is a floor, not a replacement |
| retry_after zero | sleeps `[0.25, 1.5]`; `rand_calls` 2 | `rand()` every retry; `0.0` handled |
| 400 after a retry | `BadRequestError`; 2 calls; sleeps `[0.25]` | a non-retryable error mid-sequence stops at once |
| single attempt | `ServerError`; 1 call; no sleeps | `max_attempts=1` |

## 10. Complexity

At most `max_attempts` calls and `max_attempts - 1` sleeps, so O(max_attempts) work. The worst-case wall time is the sum of the capped backoffs plus any `retry_after` values, plus each call's own latency.

The real cost is load and latency. Retries multiply traffic: three layers that each retry three times turn one failure into 27 calls. Retry at one layer only, usually the gateway. And budget total time as well as attempts: a user-facing chat turn has a deadline of a few seconds, so five attempts with an 8-second cap may be far too generous there, while a batch job can afford to wait.

## 11. If you got Wrong Answer

- **Example 2's sleep is 0.25.** You ignored `retry_after`. Take `max(delay, retry_after)`.
- **Example 3 sleeps and calls `fn` again.** You retry every exception. Catch only the retryable classes.
- **"exhausted" has five sleeps, and `t` is later than expected.** You sleep after the final failure. Raise as soon as the last attempt fails.
- **"cap reached" has sleeps of 7.92 and up.** You forgot `min(cap, ...)`.
- **Example 2's `rand_calls` is 0.** You skipped `rand()` when `retry_after` was set. Draw every time.
- **Example 1 raises `TimeoutError_`.** You caught Python's built-in `TimeoutError`. Import `TimeoutError_` from `gc_runtime`.

## 12. Follow-ups an interviewer might ask

- *What stops retries from hammering a provider that's fully down?* A circuit breaker in front of the retry loop. After enough consecutive failures it fails fast for a cool-down period, then lets one probe through (problem 125, circuit-breaker).
- *Is it safe to retry a tool call that charges a card?* Only with an idempotency key, so a retry after a lost response replays the first result instead of charging again (problem 119, idempotent-tool-execution).
- *What if one slow call blows the latency budget?* Hedge: after a deadline, send a second request to another replica or provider and take whichever answers first (problem 134, gateway-failover-hedging).
- *How does the server side produce `retry_after`?* From its rate limiter: a token bucket computes exactly how long until the request would fit (problem 123, token-bucket-rate-limiter).
- *Do SDKs already retry?* The Anthropic and OpenAI SDKs retry 429s and 5xx twice by default with backoff and jitter, and respect `retry-after`. Know what yours does, so you don't stack your own retries on top.
