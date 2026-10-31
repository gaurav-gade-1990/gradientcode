import json

from gc_runtime import ToolError


class NonDeterminismError(Exception):
    pass


def _canon(x):
    return json.dumps(x, sort_keys=True)


def run_workflow(workflow, wf_input, history, activities):
    # Bug: the workflow is allowed to finish with unconsumed history, hiding a deploy that removed a step.
    gen = workflow(wf_input)
    seq, value, error = 0, None, None
    while True:
        try:
            cmd = gen.throw(error) if error is not None else gen.send(value)
        except StopIteration as stop:
            return stop.value
        name, args = cmd
        value, error = None, None
        if seq < len(history):
            rec = history[seq]
            if rec["activity"] != name or _canon(rec["args"]) != _canon(args):
                raise NonDeterminismError("step %d: history has %s, workflow asked for %s" % (seq, rec["activity"], name))
            if rec["status"] == "completed":
                value = rec["result"]
            else:
                error = ToolError(rec["error"])
        else:
            try:
                value = activities[name](**args)
                history.append({"seq": seq, "activity": name, "args": args, "status": "completed", "result": value})
            except ToolError as e:
                history.append({"seq": seq, "activity": name, "args": args, "status": "failed", "error": str(e)})
                error = e
        seq += 1
