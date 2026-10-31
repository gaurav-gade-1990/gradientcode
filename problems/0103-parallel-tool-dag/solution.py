from collections import defaultdict

from gc_runtime import ToolError


def run_dag(loop, nodes, run_tool, max_concurrency):
    deps = {n["id"]: set(n["deps"]) for n in nodes}
    children = defaultdict(list)
    for n in nodes:
        for d in n["deps"]:
            children[d].append(n["id"])
    status = {nid: "pending" for nid in deps}
    running = [0]

    def cancel_descendants(nid):
        for c in children[nid]:
            if status[c] == "pending":
                status[c] = "cancelled"
                cancel_descendants(c)

    def fill():
        ready = sorted(nid for nid, st in status.items()
                       if st == "pending" and all(status[d] == "ok" for d in deps[nid]))
        for nid in ready:
            if running[0] >= max_concurrency:
                break
            status[nid] = "running"
            running[0] += 1
            loop.spawn(worker(nid), nid)

    def worker(nid):
        try:
            yield loop.spawn(run_tool(nid))
            status[nid] = "ok"
        except ToolError:
            status[nid] = "failed"
            cancel_descendants(nid)
        running[0] -= 1
        fill()

    fill()
    loop.run()
    return status
