def run(ns, vnodes, sessions, ops):
    """Replay membership changes against your ring and report routing and movement after each change."""
    ring = ns["HashRing"](vnodes)
    owner = {k: None for k in sessions}
    trace = []
    for op in ops:
        if op["op"] == "lookup":
            trace.append({"op": "lookup %s" % op["key"], "nodes": list(ring.get_nodes(op["key"], op["n"]))})
            continue
        if op["op"] == "add":
            ring.add_node(op["node"])
        else:
            ring.remove_node(op["node"])
        cur = {k: ring.get_node(k) for k in sessions}
        moved = [k for k in sessions if cur[k] != owner[k]]
        counts = {}
        for k in sessions:
            counts[cur[k]] = counts.get(cur[k], 0) + 1
        only = all(owner[k] == op["node"] or cur[k] == op["node"] for k in moved)
        trace.append({
            "op": "%s %s" % (op["op"], op["node"]),
            "counts": {n: counts[n] for n in sorted(counts, key=str)},
            "moved": moved,
            "only_changed_node_moved": only,
        })
        owner = cur
    return trace
