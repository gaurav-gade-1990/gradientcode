import heapq

from gc_runtime import Clock


def run(ns, calls, config):
    """Replay concurrent calls through the breaker; record decisions and every state transition."""
    clock = Clock()
    br = ns["CircuitBreaker"](clock, **config)
    timeline = []
    last = [br.state]

    def watch():
        if br.state != last[0]:
            timeline.append([round(clock.now(), 9), last[0], br.state])
            last[0] = br.state

    # (time, 0 = completion / 1 = start, order, payload)
    q = []
    for i, c in enumerate(calls):
        heapq.heappush(q, (c["t"], 1, i, None))
    decisions = [None] * len(calls)
    while q:
        t, kind, i, permit = heapq.heappop(q)
        if t > clock.now():
            clock.advance(t - clock.now())
        c = calls[i]
        if kind == 1:
            p = br.allow()
            watch()
            if p is None:
                decisions[i] = "rejected"
            else:
                decisions[i] = "allowed"
                heapq.heappush(q, (c["t"] + c["latency"], 0, i, p))
        else:
            br.record(permit, c["ok"])
            watch()
    return {"decisions": decisions, "timeline": timeline, "final": br.state}
