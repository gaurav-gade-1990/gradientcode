def run(ns, calls, **kwargs):
    """Feed proposed tool calls through the guard; a call runs only if check() returned None."""
    guard = ns["LoopGuard"](**kwargs)
    executed = []
    for step, c in enumerate(calls, start=1):
        verdict = guard.check(c["name"], c["arguments"])
        if verdict is not None:
            return {"executed": executed, "stopped_at": step, "verdict": verdict}
        executed.append(c["name"])
    return {"executed": executed, "stopped_at": None, "verdict": None}
