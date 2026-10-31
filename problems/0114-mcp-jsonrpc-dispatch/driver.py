import json

from gc_runtime import ToolError


def run(ns, server_info, tools, messages):
    """Start a server with fake order tools, feed it raw messages, and grade every reply and every tool run."""
    runs = []

    def make_handler(spec):
        def handler(arguments):
            runs.append([spec["name"], json.loads(json.dumps(arguments))])
            if "raise" in spec:
                raise ToolError(spec["raise"].format(**arguments))
            return spec["reply"].format(**arguments)
        return handler

    registered = [{"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"],
                   "handler": make_handler(t)} for t in tools]
    server = ns["McpServer"](server_info, registered)
    responses = []
    for raw in messages:
        out = server.handle(raw)
        if out is not None and not isinstance(out, str):
            raise TypeError("handle() must return a JSON string or None, got %s" % type(out).__name__)
        responses.append(None if out is None else json.loads(out))
    return {"responses": responses, "tool_runs": runs}
