from gc_runtime import RateLimitError, ServerError, TimeoutError_


def call_with_retry(fn, clock, rand, max_attempts=5, base=0.5, cap=8.0):
    last = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except (RateLimitError, ServerError, TimeoutError_) as e:
            last = e
            delay = rand() * min(cap, base * 2 ** attempt)
            if isinstance(e, RateLimitError) and e.retry_after is not None:
                delay = max(delay, e.retry_after)
            clock.sleep(delay)
    raise last
