import json


class Coalescer:
    def __init__(self, loop, upstream):
        self.loop = loop
        self.upstream = upstream
        self.inflight = {}          # key -> Task of the one upstream call for that key

    def key(self, request):
        return json.dumps([request["tenant"], request["model"], request["messages"]],
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
        response = yield from self.upstream(request)
        del self.inflight[k]          # only on success: a failed task stays in the map
        return response
