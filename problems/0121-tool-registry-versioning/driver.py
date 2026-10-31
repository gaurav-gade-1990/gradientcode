def run(ns, ops):
    """Replay register/resolve ops against one ToolRegistry; return every resolve result in order."""
    reg = ns["ToolRegistry"]()
    out = []
    for op in ops:
        if op["op"] == "register":
            reg.register(op["name"], op["version"], op.get("status", "active"))
        else:
            r = reg.resolve(op["spec"])
            if not isinstance(r, dict):
                raise TypeError("resolve(%r) must return a dict, got %r" % (op["spec"], r))
            out.append({"spec": op["spec"], "result": r})
    return out
