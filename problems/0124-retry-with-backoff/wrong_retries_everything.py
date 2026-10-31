def call_with_retry(fn, clock, rand, max_attempts=5, base=0.5, cap=8.0):
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            delay = rand() * min(cap, base * 2 ** attempt)
            ra = getattr(e, "retry_after", None)
            clock.sleep(max(delay, ra) if ra is not None else delay)
