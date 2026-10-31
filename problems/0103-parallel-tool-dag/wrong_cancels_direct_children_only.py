from collections import defaultdict

from gc_runtime import ToolError


def run_dag(loop, nodes, run_tool, max_concurrency):
    # Bug: only direct children of a failed node are cancelled. Grandchildren wait forever on a cancelled
    # dep and are reported as still pending: the run hangs in production.
    deps = {n["id"]: set(n["deps"]) for n in nodes}
    children = defaultdict(list)
    for n in nodes:
        for d in n["deps"]:
            children[d].append(n["id"])
    status = {nid: "pending" for nid in deps}
    running = [0]

    def fill():
        for nid in sorted(n for n, s in status.items() if s == "pending" and all(status[d] == "ok" for d in deps[n])):
            if running[0] >= max_concurrency:
                break
            status[nid] = "running"
            running[0] += 1
            loop.spawn(worker(nid))

    def worker(nid):
        try:
            yield loop.spawn(run_tool(nid))
            status[nid] = "ok"
        except ToolError:
            status[nid] = "failed"
            for c in children[nid]:
                if status[c] == "pending":
                    status[c] = "cancelled"
        running[0] -= 1
        fill()

    fill()
    loop.run()
    return status
