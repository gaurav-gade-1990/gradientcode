from gc_runtime import ToolError


def run_agent(llm, tools, user_msg, max_steps):
    # Bug: every tool result is tagged with the first call's id, so the model pairs results with the wrong calls.
    messages = [{"role": "user", "content": user_msg}]
    for step in range(max_steps):
        resp = llm.complete(messages, tools=list(tools))
        if resp.stop_reason == "end_turn":
            return resp.content
        if step == max_steps - 1:
            break
        messages.append({"role": "assistant", "content": resp.content,
                         "tool_calls": [tc.to_dict() for tc in resp.tool_calls]})
        first_id = resp.tool_calls[0].id
        for tc in resp.tool_calls:
            try:
                result = tools[tc.name](**tc.arguments) if tc.name in tools else "error: unknown tool " + tc.name
            except ToolError as e:
                result = "error: " + str(e)
            messages.append({"role": "tool", "tool_call_id": first_id, "content": result})
    return "STOPPED: max_steps reached"
