from gc_runtime import Clock, EventLog


def run(ns, policy, ttl, ops):
    """Replay timestamped operations against the run; report the event trail, real executions and states."""
    clock = Clock()
    log = EventLog(clock)
    executed = []

    def execute(tool, args):
        executed.append({"tool": tool, "args": args, "t": clock.now()})
        return "%s ok" % tool

    r = ns["ApprovalRun"](policy, ttl, clock, execute, log)
    states = []
    for op in ops:
        clock.advance(op["t"] - clock.now())
        kind = op["op"]
        if kind == "call":
            r.call(op["id"], op["tool"], op["args"])
        elif kind == "approve":
            r.approve(op["id"], op["by"])
        elif kind == "reject":
            r.reject(op["id"], op["by"])
        else:
            r.tick()
        states.append(r.state)
    return {"events": log.entries, "executed": executed, "states": states}
