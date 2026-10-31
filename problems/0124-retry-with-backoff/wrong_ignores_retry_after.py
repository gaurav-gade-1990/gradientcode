from gc_runtime import RateLimitError, ServerError, TimeoutError_


def call_with_retry(fn, clock, rand, max_attempts=5, base=0.5, cap=8.0):
    for attempt in range(max_attempts):
        try:
            return fn()
        except (RateLimitError, ServerError, TimeoutError_):
            if attempt == max_attempts - 1:
                raise
            clock.sleep(rand() * min(cap, base * 2 ** attempt))
