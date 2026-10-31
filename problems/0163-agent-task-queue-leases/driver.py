from gc_runtime import Clock, EventLog


def run(ns, ops, visibility_timeout=30.0, max_deliveries=3):
    """Replay timed operations against your TaskQueue. Each op happens at virtual time `at`."""
    clock = Clock()
    log = EventLog(clock)
    q = ns["TaskQueue"](clock, log, visibility_timeout, max_deliveries)
    results = []
    for op in ops:
        if op["at"] < clock.now():
            raise AssertionError("ops must be in time order")
        clock.advance(op["at"] - clock.now())
        kind = op["op"]
        if kind == "enqueue":
            out = q.enqueue(op["task"], op["priority"], op.get("payload"))
        elif kind == "lease":
            out = q.lease(op["worker"])
            out = None if out is None else dict(out)
        elif kind in ("heartbeat", "ack", "nack"):
            lease = op.get("lease")
            if "lease_from" in op:  # the lease id an earlier lease() call handed this worker
                got = results[op["lease_from"]]
                lease = got["lease_id"] if got else "ghost#1"
            out = getattr(q, kind)(lease)
        elif kind == "sweep":
            out = q.sweep()
        else:
            raise AssertionError("unknown op %r" % kind)
        results.append(out)
    return {"results": results, "events": [dict(e) for e in log.entries], "dlq": list(q.dead_letters())}
