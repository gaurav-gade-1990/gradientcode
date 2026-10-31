from gc_runtime import Clock, ServerError

MAX_CONNECTS = 60


class FakeSocket:
    def __init__(self, server, start, limit):
        self.server, self.pos, self.left = server, start, limit

    def recv(self):
        self.server.clock.advance(0.05)
        if self.left is not None and self.left <= 0:
            raise ServerError("websocket closed: 1006 abnormal closure")
        if self.pos > len(self.server.events):
            raise ServerError("websocket closed: stream already finished")
        ev = dict(self.server.events[self.pos - 1])
        self.pos += 1
        if self.left is not None:
            self.left -= 1
        return ev


class FakeChatServer:
    """Plans are consumed one per connect. A plan is {"refuse": True} or
    {"overlap": n, "skip": m, "send": k}: start at last_event_id + 1 - n + m (at least 1), send k events
    (None = to the end), then drop. Once the plans run out, connects resume cleanly to the end."""

    def __init__(self, clock, texts, plans):
        self.clock = clock
        self.events = [{"id": i + 1, "type": "delta", "text": t} for i, t in enumerate(texts)]
        self.events.append({"id": len(texts) + 1, "type": "done", "text": ""})
        self.plans = list(plans)
        self.connects = []
        self.backfills = []

    def connect(self, last_event_id):
        if len(self.connects) >= MAX_CONNECTS:
            raise AssertionError("more than %d connects: the client never stops reconnecting" % MAX_CONNECTS)
        self.connects.append(last_event_id)
        self.clock.advance(0.1)
        plan = self.plans.pop(0) if self.plans else {}
        if plan.get("refuse"):
            raise ServerError("connection refused (503)")
        start = max(1, int(last_event_id) + 1 - plan.get("overlap", 0) + plan.get("skip", 0))
        return FakeSocket(self, start, plan.get("send"))

    def backfill(self, after_id, before_id):
        self.backfills.append([after_id, before_id])
        self.clock.advance(0.2)
        return [dict(e) for e in self.events if after_id < e["id"] < before_id]


def run(ns, texts, plans, jitter, **kwargs):
    clock = Clock()
    server = FakeChatServer(clock, texts, plans)
    draws = list(jitter)
    used = []
    delivered = []

    def rand():
        if not draws:
            raise AssertionError("rand() called more times than expected")
        used.append(draws[0])
        return draws.pop(0)

    def on_event(ev):
        delivered.append(ev)

    status = ns["stream_chat"](server.connect, server.backfill, on_event, clock, rand, **kwargs)
    return {
        "status": status,
        "connect_ids": server.connects,
        "sleeps": [round(s, 9) for s in clock.sleeps],
        "backfills": server.backfills,
        "delivered_ids": [e.get("id") for e in delivered],
        "text": "".join(e.get("text", "") for e in delivered),
        "rand_calls": len(used),
        "t": round(clock.now(), 9),
    }
