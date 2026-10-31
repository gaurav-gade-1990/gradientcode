from gc_runtime import ToolError


def run_agent(llm, tools, user_msg, max_steps):
    # Bug: on the final allowed step the tools still run (side effects nobody will ever read).
    messages = [{"role": "user", "content": user_msg}]
    for step in range(max_steps):
        resp = llm.complete(messages, tools=list(tools))
        if resp.stop_reason == "end_turn":
            return resp.content
        messages.append({"role": "assistant", "content": resp.content,
                         "tool_calls": [tc.to_dict() for tc in resp.tool_calls]})
        for tc in resp.tool_calls:
            try:
                result = tools[tc.name](**tc.arguments) if tc.name in tools else "error: unknown tool " + tc.name
            except ToolError as e:
                result = "error: " + str(e)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    return "STOPPED: max_steps reached"
