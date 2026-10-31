# Bug: the flight key leaves out the model, so a Sonnet request joins an open Haiku flight
# and gets the Haiku answer.
import json


class Coalescer:
    def __init__(self, loop, upstream):
        self.loop = loop
        self.upstream = upstream
        self.inflight = {}          # key -> Task of the one upstream call for that key

    def key(self, request):
        return json.dumps([request["tenant"], request["messages"]],
                          sort_keys=True, separators=(",", ":"))

    def call(self, request):
        if request["temperature"] > 0:
            # Sampled outputs are meant to differ: never share them.
            return (yield from self.upstream(request))
        k = self.key(request)
        task = self.inflight.get(k)
        if task is None:
            task = self.loop.spawn(self._flight(k, request), name="flight")
            self.inflight[k] = task
        return (yield task)

    def _flight(self, k, request):
        try:
            return (yield from self.upstream(request))
        finally:
            # Evict when the upstream call settles, success or failure, before any waiter resumes.
            del self.inflight[k]
