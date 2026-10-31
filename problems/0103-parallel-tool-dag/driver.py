from gc_runtime import EventLoop, ToolError


def run(ns, nodes, max_concurrency):
    """Run the user's scheduler; the fake tools record their own start and end times."""
    loop = EventLoop()
    spec = {n["id"]: n for n in nodes}
    events = []
    calls = {}
    live = [0, 0]  # running now, peak

    def run_tool(nid):
        calls[nid] = calls.get(nid, 0) + 1
        n = spec[nid]

        def gen():
            live[0] += 1
            live[1] = max(live[1], live[0])
            events.append([round(loop.now(), 9), "start", nid])
            yield n["duration"]
            live[0] -= 1
            if n.get("fail"):
                events.append([round(loop.now(), 9), "fail", nid])
                raise ToolError("%s failed: %s" % (n["tool"], n["fail"]))
            events.append([round(loop.now(), 9), "finish", nid])
            return "%s ok" % n["tool"]
        return gen()

    public = [{"id": n["id"], "tool": n["tool"], "deps": list(n["deps"])} for n in nodes]
    status = ns["run_dag"](loop, public, run_tool, max_concurrency)
    return {
        "events": events,
        "status": dict(sorted((status or {}).items())),
        "peak_concurrency": live[1],
        "makespan": round(loop.now(), 9),
        "run_tool_calls": dict(sorted(calls.items())),
    }
