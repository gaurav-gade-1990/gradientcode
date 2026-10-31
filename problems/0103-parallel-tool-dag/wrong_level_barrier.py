from gc_runtime import ToolError


def run_dag(loop, nodes, run_tool, max_concurrency):
    # Bug: runs the DAG level by level (like asyncio.gather per layer). Every level waits for its slowest
    # tool, even when a fast branch's children are ready.
    deps = {n["id"]: set(n["deps"]) for n in nodes}
    status = {nid: "pending" for nid in deps}

    def one(nid, sem):
        try:
            yield loop.spawn(run_tool(nid))
            status[nid] = "ok"
        except ToolError:
            status[nid] = "failed"

    def coordinator():
        while True:
            for nid, s in status.items():
                if s == "pending" and any(status[d] in ("failed", "cancelled") for d in deps[nid]):
                    status[nid] = "cancelled"
            level = sorted(n for n, s in status.items() if s == "pending" and all(status[d] == "ok" for d in deps[n]))
            if not level:
                return
            for i in range(0, len(level), max_concurrency):
                tasks = []
                for nid in level[i:i + max_concurrency]:
                    status[nid] = "running"
                    tasks.append(loop.spawn(one(nid, None)))
                for t in tasks:
                    yield t
            changed = True
            while changed:
                changed = False
                for nid, s in status.items():
                    if s == "pending" and any(status[d] in ("failed", "cancelled") for d in deps[nid]):
                        status[nid] = "cancelled"
                        changed = True

    loop.spawn(coordinator())
    loop.run()
    return status
