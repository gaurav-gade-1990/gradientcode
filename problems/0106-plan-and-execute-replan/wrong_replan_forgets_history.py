import json

from gc_runtime import ToolError

PLANNER = "You are the planner. Reply with only a JSON list of steps, each {\"id\", \"tool\", \"args\"}."


def execute_plan(llm, tools, goal, max_replans):
    # Bug: the replan call only reports the failure, so the planner can't see what already happened and re-plans from scratch.
    completed, results = [], {}

    def plan(failed):
        payload = json.dumps({"goal": goal, "completed": completed if failed is None else [], "failed": failed}, sort_keys=True)
        resp = llm.complete([{"role": "system", "content": PLANNER}, {"role": "user", "content": payload}])
        return json.loads(resp.content)

    def run_step(step):
        args = {}
        for k, v in step["args"].items():
            if isinstance(v, dict) and set(v) == {"$ref"}:
                if v["$ref"] not in results:
                    return None, "unresolved reference " + v["$ref"]
                v = results[v["$ref"]]
            args[k] = v
        if step["tool"] not in tools:
            return None, "unknown tool " + step["tool"]
        try:
            return tools[step["tool"]](**args), None
        except ToolError as e:
            return None, str(e)

    steps, i, replans = plan(None), 0, 0
    while i < len(steps):
        step = steps[i]
        if step["id"] in results:
            i += 1
            continue
        result, error = run_step(step)
        if error is None:
            results[step["id"]] = result
            completed.append({"id": step["id"], "tool": step["tool"], "result": result})
            i += 1
            continue
        if replans >= max_replans:
            return {"status": "failed", "completed": [c["id"] for c in completed], "replans": replans, "results": results}
        replans += 1
        steps, i = plan({"id": step["id"], "tool": step["tool"], "error": error}), 0
    return {"status": "completed", "completed": [c["id"] for c in completed], "replans": replans, "results": results}
