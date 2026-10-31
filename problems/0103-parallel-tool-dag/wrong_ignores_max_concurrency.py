from collections import defaultdict

from gc_runtime import ToolError


def run_dag(loop, nodes, run_tool, max_concurrency):
    # Bug: every ready node starts at once. Against a real API this is a 429 storm.
    deps = {n["id"]: set(n["deps"]) for n in nodes}
    children = defaultdict(list)
    for n in nodes:
        for d in n["deps"]:
            children[d].append(n["id"])
    status = {nid: "pending" for nid in deps}

    def cancel(nid):
        for c in children[nid]:
            if status[c] == "pending":
                status[c] = "cancelled"
                cancel(c)

    def fill():
        for nid in sorted(n for n, s in status.items() if s == "pending" and all(status[d] == "ok" for d in deps[n])):
            status[nid] = "running"
            loop.spawn(worker(nid))

    def worker(nid):
        try:
            yield loop.spawn(run_tool(nid))
            status[nid] = "ok"
        except ToolError:
            status[nid] = "failed"
            cancel(nid)
        fill()

    fill()
    loop.run()
    return status
