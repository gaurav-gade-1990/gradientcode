from gc_runtime import Clock, FakeLLM, GCError


def run(ns, script, jitter, **kwargs):
    """Drive call_with_retry against a scripted provider; report calls, sleeps and the outcome."""
    clock = Clock()
    llm = FakeLLM(script, clock=clock, latency=0.25)
    draws = list(jitter)
    used = []

    def rand():
        if not draws:
            raise AssertionError("rand() called more times than there were retries")
        used.append(draws[0])
        return draws.pop(0)

    def fn():
        return llm.complete([{"role": "user", "content": "summarize the ticket"}]).content

    try:
        out = {"returned": ns["call_with_retry"](fn, clock, rand, **kwargs), "raised": None}
    except GCError as e:
        out = {"returned": None, "raised": type(e).__name__}
    out.update(calls=len(llm.calls), sleeps=[round(s, 9) for s in clock.sleeps], rand_calls=len(used), t=round(clock.now(), 9))
    return out
