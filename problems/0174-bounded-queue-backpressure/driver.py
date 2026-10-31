from gc_runtime import Clock, EventLoop, Task


class Loop(EventLoop):
    """EventLoop plus the two helpers this problem needs: a pending future and a way to complete it."""

    def future(self, name="future"):
        return Task(self, None, name)

    def resolve(self, fut, value=None):
        if not isinstance(fut, Task) or fut.gen is not None:
            raise TypeError("resolve() takes a future made by loop.future()")
        if fut.done:
            raise RuntimeError("future resolved twice")
        self._finish(fut, value, None)


def _r(x):
    return round(x, 9)


def run(ns, capacity, policy, producers, consumers):
    loop = Loop(Clock())
    q = ns["BoundedQueue"](loop, capacity, policy)
    events = []
    blocked = {p["name"]: 0.0 for p in producers}
    finished = []
    delivered = []

    def producer(p):
        if p.get("start"):
            yield p["start"]
        for item in p["items"]:
            t0 = loop.now()
            n_drop = len(q.dropped)
            ok = yield from q.put(item)
            blocked[p["name"]] += loop.now() - t0
            for d in q.dropped[n_drop:]:
                events.append([_r(loop.now()), "drop", p["name"], d])
            events.append([_r(loop.now()), "put" if ok else "reject", p["name"], item])
            if len(q) > capacity:
                events.append([_r(loop.now()), "overflow", p["name"], len(q)])
            yield p["interval"]
        finished.append(p["name"])

    def consumer(c):
        while True:
            item = yield from q.get()
            if len(delivered) + sum(1 for e in events if e[1] == "get") > 2 * total:
                raise AssertionError("consumers received more items than were produced")
            events.append([_r(loop.now()), "get", c["name"], item])
            yield c["service"]
            events.append([_r(loop.now()), "done", c["name"], item])
            delivered.append(item)

    total = sum(len(p["items"]) for p in producers)
    for p in producers:
        loop.spawn(producer(p), p["name"])
    for c in consumers:
        loop.spawn(consumer(c), c["name"])
    loop.run(until=10000.0)
    done_times = [e[0] for e in events if e[1] == "done"]
    makespan = max(done_times) if done_times else 0.0
    return {
        "events": events,
        "dropped": list(q.dropped),
        "rejected": list(q.rejected),
        "max_depth": int(q.max_depth),
        "blocked_s": {k: _r(v) for k, v in blocked.items()},
        "stuck_producers": [p["name"] for p in producers if p["name"] not in finished],
        "delivered": len(delivered),
        "makespan": _r(makespan),
        "throughput": _r(len(delivered) / makespan) if makespan else 0.0,
    }
