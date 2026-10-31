# Incident: an error from the primary was treated like slowness. The gateway sat idle until the
# hedge timer fired before trying the secondary, adding the full hedge delay to every failover.
def handle_request(client, request, providers, hedge_delay, deadline):
    queue = list(providers)
    inflight = []
    last = [0.0]

    def send_next():
        while queue:
            p = queue.pop(0)
            if client.is_open(p):
                continue                      # skipped for good
            inflight.append(client.send(p, request))
            last[0] = client.now()
            return True
        return False

    def give_up(status):
        for a in inflight:
            client.cancel(a)
        return {"status": status, "provider": None, "text": None}

    if not send_next():
        return {"status": "unavailable", "provider": None, "text": None}
    while True:
        if not inflight:                      # fail over at once
            if client.now() >= deadline:
                return give_up("timeout")
            wait = last[0] + hedge_delay - client.now()
            if wait > 0 and queue:
                yield from client.wait_any([], wait)
            if not send_next():
                return give_up("failed")
            continue
        wake = deadline
        if len(inflight) == 1 and queue:
            wake = min(wake, inflight[0].start + hedge_delay)
        # A completion at the same instant as a timer is returned first.
        a = yield from client.wait_any(inflight, max(0.0, wake - client.now()))
        if a is None:
            if client.now() >= deadline:
                return give_up("timeout")
            send_next()                       # the hedge timer fired
            continue
        inflight.remove(a)
        if a.ok:
            for other in inflight:
                client.cancel(other)
            return {"status": "ok", "provider": a.provider, "text": a.text}
