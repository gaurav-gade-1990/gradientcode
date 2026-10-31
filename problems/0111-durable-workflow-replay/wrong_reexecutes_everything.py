from gc_runtime import ToolError


class NonDeterminismError(Exception):
    pass


def run_workflow(workflow, wf_input, history, activities):
    # Bug: "resume" just reruns the workflow from the top. Every crash charges the card again.
    gen = workflow(wf_input)
    value, error = None, None
    while True:
        try:
            name, args = gen.throw(error) if error is not None else gen.send(value)
        except StopIteration as stop:
            return stop.value
        value, error = None, None
        try:
            value = activities[name](**args)
            history.append({"seq": len(history), "activity": name, "args": args, "status": "completed", "result": value})
        except ToolError as e:
            history.append({"seq": len(history), "activity": name, "args": args, "status": "failed", "error": str(e)})
            error = e
