from gc_runtime import Clock, EventLoop


class Attempt:
    """One request sent to one provider. Its fate is scripted; you learn it only through wait_any."""

    def __init__(self, client, provider, index, start, end, outcome, output_tokens):
        self._client = client
        self.provider = provider
        self.index = index
        self.start = start
        self._end = end
        self._outcome = outcome
        self._output_tokens = output_tokens
        self.cancelled_at = None

    @property
    def done(self):
        return self.cancelled_at is None and self._end <= self._client.now()

    def _require_done(self):
        if not self.done:
            raise RuntimeError("attempt to %s is still in flight (or was cancelled)" % self.provider)

    @property
    def ok(self):
        self._require_done()
        return self._outcome == "ok"

    @property
    def error(self):
        self._require_done()
        return None if self._outcome == "ok" else self._outcome

    @property
    def text(self):
        self._require_done()
        return "%s: answer" % self.provider if self._outcome == "ok" else None


class Client:
    def __init__(self, loop, providers, script, request):
        self._loop = loop
        self._providers = {p["name"]: p for p in providers}
        self._script = script
        self._request = request
        self.attempts = []

    def now(self):
        return self._loop.now()

    def is_open(self, provider):
        return self.now() < self._providers[provider].get("open_until", 0)

    def send(self, provider, request):
        now = self.now()
        if self.is_open(provider):
            a = Attempt(self, provider, len(self.attempts), now, now, "circuit_open", 0)
        else:
            s = self._script[provider]
            a = Attempt(self, provider, len(self.attempts), now, now + s["latency"], s["outcome"], s.get("output_tokens", 0))
        self.attempts.append(a)
        return a

    def cancel(self, attempt):
        if attempt.cancelled_at is None and attempt._end > self.now():
            attempt.cancelled_at = self.now()

    def wait_any(self, attempts, timeout=None):
        """Use as `a = yield from client.wait_any(attempts, timeout)`. Returns an Attempt, or None on timeout."""
        live = [a for a in attempts if a.cancelled_at is None]
        now = self.now()
        if not live:
            if timeout is None:
                raise RuntimeError("wait_any on no live attempts with no timeout would wait forever")
            yield max(0.0, timeout)
            return None
        first = min(live, key=lambda a: (a._end, a.index))
        if timeout is None or first._end <= now + timeout:
            yield max(0.0, first._end - now)
            return first
        yield max(0.0, timeout)
        return None


def run(ns, providers, script, request, hedge_delay, deadline):
    clock = Clock()
    loop = EventLoop(clock)
    client = Client(loop, providers, script, request)
    names = [p["name"] for p in providers]
    res = ns["handle_request"](client, request, names, hedge_delay, deadline)
    t_return = 0.0
    if hasattr(res, "send") and hasattr(res, "throw"):
        task = loop.spawn(res, "handler")
        loop.run()
        if task.error is not None:
            raise task.error
        res, t_return = task.result, task.finished_at
    prices = {p["name"]: p for p in providers}
    cost, log = 0.0, []
    for a in client.attempts:
        p = prices[a.provider]
        if a._outcome == "circuit_open":
            outcome, end = "circuit_open", a.start
        elif a.cancelled_at is not None:
            outcome, end = "cancelled", a.cancelled_at
            cost += request["input_tokens"] * p["input_per_mtok"] / 1e6      # prompt already processed
        else:
            outcome, end = a._outcome, a._end                               # finishes, even in the background
            if outcome == "ok":
                cost += (request["input_tokens"] * p["input_per_mtok"] + a._output_tokens * p["output_per_mtok"]) / 1e6
        log.append({"provider": a.provider, "start": round(a.start, 9), "end": round(end, 9), "outcome": outcome})
    return {"result": res, "attempts": log, "cost": round(cost, 12), "t": round(t_return, 9)}
