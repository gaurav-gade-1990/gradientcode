from gc_runtime import ToolError

SENTINEL = "STOPPED: max_steps reached"


def run_agent(llm, tools, user_msg, max_steps):
    messages = [{"role": "user", "content": user_msg}]
    for step in range(max_steps):
        resp = llm.complete(messages, tools=list(tools))
        if resp.stop_reason == "end_turn":
            return resp.content
        if step == max_steps - 1:
            break
        messages.append({"role": "assistant", "content": resp.content,
                         "tool_calls": [tc.to_dict() for tc in resp.tool_calls]})
        for tc in resp.tool_calls:
            if tc.name not in tools:
                result = "error: unknown tool " + tc.name
            else:
                try:
                    result = tools[tc.name](**tc.arguments)
                except ToolError as e:
                    result = "error: " + str(e)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    return SENTINEL
