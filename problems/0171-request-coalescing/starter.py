import json


class Coalescer:
    def __init__(self, loop, upstream):
        self.loop = loop
        self.upstream = upstream

    def call(self, request):
        # Write your code here. This must be a generator: callers do `resp = yield from coalescer.call(req)`.
        yield None
