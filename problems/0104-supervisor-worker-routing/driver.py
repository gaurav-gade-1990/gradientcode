from gc_runtime import ToolError


def run(ns, subtasks, workers, down=(), fail_pairs=()):
    """`down` workers fail every call; a [worker, subtask] pair in `fail_pairs` fails that call."""
    titles = {t["id"]: t["title"] for t in subtasks}
    bad = {tuple(p) for p in fail_pairs}
    calls = []

    def execute(worker, subtask_id):
        calls.append([worker, subtask_id])
        if worker in down:
            raise ToolError("%s is unavailable" % worker)
        if (worker, subtask_id) in bad:
            raise ToolError("%s crashed on %s" % (worker, subtask_id))
        return "%s: %s (done)" % (worker, titles[subtask_id])

    results = ns["supervise"](subtasks, workers, execute)
    return {"results": results, "execute_calls": calls}
