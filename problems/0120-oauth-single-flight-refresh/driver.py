from gc_runtime import BadRequestError, EventLoop, GCError


def _r(x):
    return round(float(x), 9)


def run(ns, requests, expires_at, refresh_outcomes, refresh_latency=0.5, token_ttl=None):
    """Fire concurrent tool calls at an OAuth-protected API whose token expires; record sends and refreshes."""
    loop = EventLoop()
    expiry = {"tok_0": float(expires_at)}
    issued = [0]
    outcomes = list(refresh_outcomes)
    sends, refreshes, results = [], [], {}

    def send(token, request):
        yield request.get("latency", 0.1)
        now = loop.now()
        valid = token in expiry and (expiry[token] is None or now < expiry[token])
        status = 200 if valid else 401
        sends.append([_r(now), request["id"], token, status])
        if status == 200:
            return {"status": 200, "body": "%s ok for %s" % (request["tool"], request["id"])}
        return {"status": 401, "body": "invalid_token"}

    def refresh():
        refreshes.append(_r(loop.now()))
        yield refresh_latency
        outcome = outcomes.pop(0) if outcomes else "ok"
        if outcome != "ok":
            raise BadRequestError("invalid_grant")
        issued[0] += 1
        tok = "tok_%d" % issued[0]
        expiry[tok] = None if token_ttl is None else loop.now() + token_ttl
        return tok

    client = ns["AuthClient"](loop, "tok_0", refresh, send)

    def job(req):
        yield req["at"]
        try:
            resp = yield from client.call(dict(req))
            res = {"status": resp["status"], "body": resp["body"]}
        except GCError as e:
            res = {"raised": type(e).__name__}
        res["t"] = _r(loop.now())
        results[req["id"]] = res

    for req in requests:
        loop.spawn(job(req), req["id"])
    loop.run()
    return {
        "results": {req["id"]: results.get(req["id"], {"raised": "never finished"}) for req in requests},
        "refreshes": refreshes,
        "sends": sends,
        "token": client.token,
    }
