from collections import defaultdict

from gc_runtime import ToolError


def run_dag(loop, nodes, run_tool, max_concurrency):
    # Bug: ready nodes start in the planner's list order, not id order, so runs aren't reproducible
    # when the planner reorders its output.
    order = [n["id"] for n in nodes]
    deps = {n["id"]: set(n["deps"]) for n in nodes}
    children = defaultdict(list)
    for n in nodes:
        for d in n["deps"]:
            children[d].append(n["id"])
    status = {nid: "pending" for nid in order}
    running = [0]

    def cancel(nid):
        for c in children[nid]:
            if status[c] == "pending":
                status[c] = "cancelled"
                cancel(c)

    def fill():
        for nid in [n for n in order if status[n] == "pending" and all(status[d] == "ok" for d in deps[n])]:
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
            cancel(nid)
        running[0] -= 1
        fill()

    fill()
    loop.run()
    return status
