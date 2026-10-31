from collections import defaultdict

from gc_runtime import ToolError


def run_dag(loop, nodes, run_tool, max_concurrency):
    # Bug: one failed tool cancels every pending node, including branches that never depended on it.
    deps = {n["id"]: set(n["deps"]) for n in nodes}
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
            for k, s in status.items():
                if s == "pending":
                    status[k] = "cancelled"
        running[0] -= 1
        fill()

    fill()
    loop.run()
    return status
