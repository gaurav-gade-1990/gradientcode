from gc_runtime import BadRequestError, Clock, EventLoop, ToolError


def run(ns, subscribers, channels, latency, outcomes):
    """Run fanout against scripted channel sends; grade the send trace, the results and the end time.

    outcomes[sid] is the list of results for that subscriber's attempts in order ("ok", "fail", "reject");
    once it runs out, sends succeed.
    """
    loop = EventLoop(Clock())
    script = {k: list(v) for k, v in outcomes.items()}
    attempts = []

    def send(subscriber_id, channel):
        seq = script.get(subscriber_id) or []
        outcome = seq.pop(0) if seq else "ok"
        attempts.append([round(loop.now(), 9), channel, subscriber_id, outcome])
        yield latency[channel]
        if outcome == "fail":
            raise ToolError("%s send to %s failed (503)" % (channel, subscriber_id))
        if outcome == "reject":
            raise BadRequestError("%s rejected %s (unknown recipient)" % (channel, subscriber_id))
        return True

    res = ns["fanout"](loop, [dict(s) for s in subscribers], {k: dict(v) for k, v in channels.items()}, send)
    if not isinstance(res, dict):
        raise TypeError("fanout must return {'delivered': ..., 'failed': ...}, got %r" % (res,))
    delivered = {k: round(float(v), 9) for k, v in dict(res.get("delivered") or {}).items()}
    return {"delivered": delivered, "failed": dict(res.get("failed") or {}), "attempts": attempts,
            "t": round(loop.now(), 9)}
