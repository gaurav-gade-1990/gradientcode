# Incident: the gateway returned the hedge winner but never cancelled the loser. Every hedged
# request was billed twice in full, and hedging added 30% to the monthly provider bill.
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
            if client.now() >= deadline:
                return give_up("timeout")
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
            return {"status": "ok", "provider": a.provider, "text": a.text}
