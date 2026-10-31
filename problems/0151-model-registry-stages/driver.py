def run(ns, ops):
    """Run a script of [method, kwargs] calls against your registry; record every return value and the events."""
    reg = ns["ModelRegistry"]()
    results = []
    for method, kwargs in ops:
        results.append([method, getattr(reg, method)(**kwargs)])
    return {"results": results, "events": [dict(e) for e in reg.events]}
