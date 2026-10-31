import json

from gc_runtime import ToolError


class NonDeterminismError(Exception):
    pass


def run_workflow(workflow, wf_input, history, activities):
    # Bug: new events are buffered and written to the durable history only when the workflow finishes.
    # A crash loses every event of the run, so the next attempt repeats the side effects.
    gen = workflow(wf_input)
    seq, value, error, pending = 0, None, None, []
    while True:
        try:
            cmd = gen.throw(error) if error is not None else gen.send(value)
        except StopIteration as stop:
            if seq < len(history):
                raise NonDeterminismError("leftover history")
            history.extend(pending)
            return stop.value
        name, args = cmd
        value, error = None, None
        if seq < len(history):
            rec = history[seq]
            if rec["activity"] != name or json.dumps(rec["args"], sort_keys=True) != json.dumps(args, sort_keys=True):
                raise NonDeterminismError("step %d" % seq)
            if rec["status"] == "completed":
                value = rec["result"]
            else:
                error = ToolError(rec["error"])
        else:
            try:
                value = activities[name](**args)
                pending.append({"seq": seq, "activity": name, "args": args, "status": "completed", "result": value})
            except ToolError as e:
                pending.append({"seq": seq, "activity": name, "args": args, "status": "failed", "error": str(e)})
                error = e
        seq += 1
