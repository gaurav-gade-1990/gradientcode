class AuthClient:
    def __init__(self, loop, token, refresh, send):
        self.loop = loop
        self.token = token
        self.refresh = refresh
        self.send = send
        self._inflight = None  # the one refresh Task currently running, if any

    def _refresh_task(self):
        try:
            token = yield from self.refresh()
            self.token = token
            return token
        finally:
            self._inflight = None

    def call(self, request):
        sent_with = self.token
        resp = yield from self.send(sent_with, request)
        if resp["status"] != 401:
            return resp
        if self._inflight is not None:
            yield self._inflight
        else:
            self._inflight = self.loop.spawn(self._refresh_task(), "refresh")
            yield self._inflight
        # else: someone refreshed while our request was in flight; just retry
        return (yield from self.send(self.token, request))
