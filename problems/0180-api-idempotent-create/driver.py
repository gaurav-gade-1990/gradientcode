import copy

from gc_runtime import Clock, EventLoop, ServerError

HORIZON = 30.0


class FakeRunsDB:
    """An idempotency-key table plus a runs table. Only claim() is atomic."""

    def __init__(self, loop, fail_creates):
        self.loop = loop
        self.keys = {}
        self.runs = []
        self.fail = set(fail_creates)
        self.creates = 0

    def _k(self, key):
        return tuple(key) if isinstance(key, list) else key

    def claim(self, key, fingerprint):
        key = self._k(key)
        if key in self.keys:
            return copy.deepcopy(self.keys[key])
        self.keys[key] = {"fingerprint": fingerprint, "status": "pending", "response": None}
        return None

    def get(self, key):
        rec = self.keys.get(self._k(key))
        return copy.deepcopy(rec) if rec is not None else None

    def put(self, key, record):
        self.keys[self._k(key)] = copy.deepcopy(record)

    def complete(self, key, response):
        rec = self.keys.setdefault(self._k(key), {"fingerprint": None, "status": "pending", "response": None})
        rec["status"] = "done"
        rec["response"] = copy.deepcopy(response)

    def release(self, key):
        self.keys.pop(self._k(key), None)

    def create_run(self, user_id, body):
        n = self.creates
        self.creates += 1
        yield 0.2
        if n in self.fail:
            raise ServerError("runs insert failed")
        run_id = "run_%03d" % (len(self.runs) + 1)
        self.runs.append({"id": run_id, "user": user_id})
        return run_id


def run(ns, requests, fail_creates=()):
    """Fire each request at its arrival time; report every response, the runs created and the attempts."""
    loop = EventLoop(Clock())
    db = FakeRunsDB(loop, fail_creates)
    handler = ns["handle_create_run"]
    responses = [None] * len(requests)

    def client(i, req):
        if req["at"] > 0:
            yield req["at"]
        gen = handler(db, req["user"], dict(req["headers"]), copy.deepcopy(req["body"]))
        if not hasattr(gen, "send"):
            raise TypeError("handle_create_run must be a generator (use yield / yield from)")
        resp = yield from gen
        if not isinstance(resp, dict):
            raise TypeError("handle_create_run must return a response dict, got %r" % (resp,))
        responses[i] = {"status": resp.get("status"), "run_id": resp.get("run_id"),
                        "replayed": bool(resp.get("replayed")), "t": round(loop.now(), 9)}

    for i, req in enumerate(requests):
        loop.spawn(client(i, req), "req-%d" % i)
    loop.run(until=HORIZON)
    out = [r if r is not None else "timeout" for r in responses]
    return {"responses": out, "runs": db.runs, "create_attempts": db.creates}
