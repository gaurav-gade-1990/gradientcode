def run(ns, hists, ops):
    """Drive LatencyHistogram objects through a scenario and record every observable result.

    hists: {name: {"alpha": float, "max_buckets": int}} (either key optional).
    ops: a list of steps; see the per-op handling below. Every step appends one trace entry.
    """
    H = ns["LatencyHistogram"]
    objs = {name: H(**cfg) for name, cfg in hists.items()}

    def snap(name):
        h = objs[name]
        return {"count": int(h.count()), "buckets": [[int(i), int(c)] for i, c in h.buckets()]}

    def num(x):
        return None if x is None else float(x)

    trace = []
    for op in ops:
        kind = op["op"]
        if kind == "record":
            h = objs[op["h"]]
            accepted = rejected = 0
            items = [(v, 1) for v in op["values"]] if "values" in op else [(op["value"], op.get("count", 1))]
            for v, c in items:
                try:
                    h.record(v, c)
                    accepted += 1
                except ValueError:
                    rejected += 1
            trace.append({"op": "record", "h": op["h"], "accepted": accepted, "rejected": rejected, "count": int(h.count())})
        elif kind == "merge":
            before = snap(op["from"])
            try:
                objs[op["into"]].merge(objs[op["from"]])
                status = "ok"
            except ValueError:
                status = "ValueError"
            trace.append({"op": "merge", "into": op["into"], "from": op["from"], "status": status,
                          "source_unchanged": snap(op["from"]) == before, "count": int(objs[op["into"]].count())})
        elif kind == "quantile":
            h = objs[op["h"]]
            vals = []
            for q in op["qs"]:
                try:
                    vals.append(num(h.quantile(q)))
                except ValueError:
                    vals.append("ValueError")
            trace.append({"op": "quantile", "h": op["h"], "qs": list(op["qs"]), "values": vals})
        elif kind == "snapshot":
            trace.append(dict({"op": "snapshot", "h": op["h"]}, **snap(op["h"])))
        else:
            raise ValueError("unknown op %r" % kind)
    return {"trace": trace, "final": {name: snap(name) for name in sorted(objs)}}
