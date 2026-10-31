import json

from gc_runtime import FakeLLM, ToolError


def run(ns, script, tool_table, user_msg, max_steps):
    """Run the agent against a scripted model and table-backed tools; report the whole trace."""
    llm = FakeLLM(script)
    ran = []

    def make(name, rows):
        table = {json.dumps(r["args"], sort_keys=True): r for r in rows}

        def tool(**kwargs):
            ran.append({"name": name, "arguments": kwargs})
            row = table.get(json.dumps(kwargs, sort_keys=True))
            if row is None:
                raise ToolError("no record matches %s" % json.dumps(kwargs, sort_keys=True))
            if "error" in row:
                raise ToolError(row["error"])
            return row["result"]
        return tool

    tools = {name: make(name, rows) for name, rows in tool_table.items()}
    answer = ns["run_agent"](llm, tools, user_msg, max_steps)
    return {
        "answer": answer,
        "model_calls": [c["messages"] for c in llm.calls],
        "tools_offered": [c["tools"] for c in llm.calls],
        "tool_runs": ran,
    }
