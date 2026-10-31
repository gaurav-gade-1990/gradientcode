import json

from gc_runtime import ToolError


class NonDeterminismError(Exception):
    pass


def _canon(x):
    return json.dumps(x, sort_keys=True)


def run_workflow(workflow, wf_input, history, activities):
    # Bug: recorded results are fed back by position without checking which activity they belong to. After a deploy the shipment id is handed to the email step, silently.
    gen = workflow(wf_input)
    seq, value, error = 0, None, None
    while True:
        try:
            cmd = gen.throw(error) if error is not None else gen.send(value)
        except StopIteration as stop:
            if seq < len(history):
                raise NonDeterminismError("workflow finished but history has %d more events" % (len(history) - seq))
            return stop.value
        name, args = cmd
        value, error = None, None
        if seq < len(history):
            rec = history[seq]
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
