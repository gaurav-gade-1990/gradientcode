from gc_runtime import ERRORS, Clock, EventLoop, GCError


def run(ns, requests, upstream_script):
    """Each request is a client task on the EventLoop. It sleeps until its arrival time, then awaits the
    coalescer. The upstream provider consumes upstream_script in call order and records every call."""
    loop = EventLoop(Clock())
    script = list(upstream_script)
    calls = []

    def upstream(request):
        i = len(calls)
        if i >= len(script):
            raise GCError("upstream script exhausted after %d calls" % i)
        turn = script[i]
        calls.append({"t": loop.now(), "request_id": request["request_id"], "tenant": request["tenant"]})
        yield float(turn["latency"])
        if "error" in turn:
            raise ERRORS[turn["error"]](turn["error"])
        return {"id": "resp_%d" % i, "tenant": request["tenant"], "content": turn["content"]}

    coalescer = ns["Coalescer"](loop, upstream)
    results = [None] * len(requests)

    def client(i, req):
        yield float(req["at"])
        start = loop.now()
        payload = {k: v for k, v in req.items() if k != "at"}
        try:
            resp = yield from coalescer.call(payload)
            results[i] = {"request_id": req["request_id"], "start": start, "end": loop.now(),
                          "response_id": resp["id"], "response_tenant": resp["tenant"], "content": resp["content"]}
        except GCError as e:
            results[i] = {"request_id": req["request_id"], "start": start, "end": loop.now(), "error": type(e).__name__}

    for i, req in enumerate(requests):
        loop.spawn(client(i, req), name=req["request_id"])
    loop.run()
    if any(r is None for r in results):
        raise RuntimeError("some requests never completed: a waiter was never woken")
    return {"responses": results, "upstream_calls": calls, "t": loop.now()}
