import json

from gc_runtime import FakeLLM, ToolError


def run(ns, goal, plans, tool_table, max_replans):
    """`plans` are the planner's replies in order; tools answer from `tool_table` keyed by their resolved args."""
    llm = FakeLLM([{"content": json.dumps(p)} for p in plans])
    log = []

    def make(name, rows):
        table = {json.dumps(r["args"], sort_keys=True): r for r in rows}

        def tool(**kwargs):
            log.append({"tool": name, "args": kwargs})
            row = table.get(json.dumps(kwargs, sort_keys=True))
            if row is None:
                raise ToolError("%s: bad arguments %s" % (name, json.dumps(kwargs, sort_keys=True)))
            if "error" in row:
                raise ToolError(row["error"])
            return row["result"]
        return tool

    tools = {name: make(name, rows) for name, rows in tool_table.items()}
    out = ns["execute_plan"](llm, tools, goal, max_replans)
    return {"returned": out, "planner_calls": [c["messages"] for c in llm.calls], "tool_calls": log}
