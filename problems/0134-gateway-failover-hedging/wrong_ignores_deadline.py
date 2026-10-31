# Incident: no overall deadline. When every provider hung, the request held a worker and a user's
# spinner for 60 s, and the hung attempts were all billed when they finally finished.
def handle_request(client, request, providers, hedge_delay, deadline):
    queue = list(providers)
    inflight = []

    def send_next():
        while queue:
            p = queue.pop(0)
            if client.is_open(p):
                continue                      # skipped for good
            inflight.append(client.send(p, request))
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
            if not send_next():
                return give_up("failed")
            continue
        timeout = None
        if len(inflight) == 1 and queue:
            timeout = max(0.0, inflight[0].start + hedge_delay - client.now())
        a = yield from client.wait_any(inflight, timeout)
        if a is None:
            send_next()                       # the hedge timer fired
            continue
        inflight.remove(a)
        if a.ok:
            for other in inflight:
                client.cancel(other)
            return {"status": "ok", "provider": a.provider, "text": a.text}
