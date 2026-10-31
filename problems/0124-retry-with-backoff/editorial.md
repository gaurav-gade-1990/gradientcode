## Approach

Production retry logic answers three questions: **whether** to retry, **how long** to wait, and **when** to give up.

```python
RETRYABLE = (RateLimitError, ServerError, TimeoutError_)

def call_with_retry(fn, clock, rand, max_attempts=5, base=0.5, cap=8.0):
    for attempt in range(max_attempts):
        try:
            return fn()
        except RETRYABLE as e:
            if attempt == max_attempts - 1:
                raise
            delay = rand() * min(cap, base * 2 ** attempt)
            if isinstance(e, RateLimitError) and e.retry_after is not None:
                delay = max(delay, e.retry_after)
            clock.sleep(delay)
```

**Why full jitter?** Suppose a provider hiccups and 1,000 agents all fail at the same moment. With fixed exponential backoff they all retry at exactly 0.5 s, then at 1 s, and so on, in synchronized waves that keep the provider down. Drawing the delay uniformly from `[0, backoff]` spreads the load out. AWS's analysis found full jitter does the least total work of the common variants.

**Why honor `Retry-After`?** The server knows its own recovery time. Retrying sooner just burns your quota on more 429s, and some providers penalize clients that ignore the header.

## Common mistakes

- **Retrying everything.** A 400 (bad schema, prompt too long) fails identically on every try. You waste the full backoff and hide the real bug.
- **Ignoring `Retry-After`.** This hammers a rate-limited provider and stretches out the outage.
- **No cap.** `base * 2**k` grows without bound. By attempt 10 you're sleeping minutes inside a user request.
- **Sleeping after the final failure.** That adds latency for nothing before raising.

## Production notes

- Put this in **one gateway** that every model call goes through, not copied into each agent. Then retries, timeouts, tracing and cost accounting are written once.
- Budget the **total** time as well as the attempts. A user-facing chat turn usually has a deadline of a few seconds, while batch jobs can wait minutes.
- Retries multiply load. With 3 layers that each retry 3 times, one failure turns into 27 calls. Retry at one layer only, and pair retries with a **circuit breaker** (problem 125) so a dead provider fails fast.
- Only retry **idempotent** operations. A tool call that charges a card needs an idempotency key (problem 119, idempotent-tool-execution) before it's safe to retry.
- The Anthropic and OpenAI SDKs retry 429/5xx twice by default with exponential backoff and jitter, and they respect `retry-after`. Know what your SDK already does, so you don't stack your own retries on top of it.
