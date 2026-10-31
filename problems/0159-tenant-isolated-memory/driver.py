def run(ns, ops):
    """Replay a sequence of agent memory operations against your MemoryStore and record each result."""
    store = ns["MemoryStore"]()
    results = []
    for op in ops:
        kind = op["op"]
        try:
            if kind == "write":
                out = store.write(op["ctx"], op["key"], op["value"], op.get("scope", "private"), list(op.get("sources", [])))
            elif kind == "read":
                out = store.read(op["ctx"], op["key"])
            elif kind == "visible":
                out = list(store.visible(op["ctx"]))
            elif kind == "delete_user":
                out = list(store.delete_user(op["tenant"], op["user"]))
            else:
                raise AssertionError("unknown op %r" % kind)
        except (PermissionError, ValueError) as e:
            out = {"error": type(e).__name__}
        results.append(out)
    return results
