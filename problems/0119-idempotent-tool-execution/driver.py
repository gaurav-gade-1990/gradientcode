import json

from gc_runtime import Clock, ToolError


def run(ns, ttl, ops):
    """Replay agent tool calls at virtual times; record what really executed downstream."""
    clock = Clock()
    ex = ns["IdempotentExecutor"](clock, ttl)
    runs = []

    def make_fn(op):
        def fn(args):
            runs.append({"t": clock.now(), "tool": op["tool"], "args": json.loads(json.dumps(args)), "ok": "fail" not in op})
            if "fail" in op:
                raise ToolError(op["fail"])
            n = len(runs)
            if op["tool"] == "charge_card":
                return {"charge_id": "ch_%03d" % n, "amount_cents": args.get("amount_cents")}
            return {"effect_id": "%s_%03d" % (op["tool"], n)}
        return fn

    results = []
    for op in ops:
        if op["at"] > clock.now():
            clock.advance(op["at"] - clock.now())
        results.append(ex.execute(op.get("key"), op["tool"], op["args"], make_fn(op)))
    return {"results": results, "tool_runs": runs}
