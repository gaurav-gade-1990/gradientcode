from gc_runtime import ToolError


def run_agent(llm, tools, user_msg, max_steps):
    # Bug: tool results are appended without the assistant turn that requested them.
    # Real providers answer this transcript with a 400 ("tool_result without matching tool_use").
    messages = [{"role": "user", "content": user_msg}]
    for step in range(max_steps):
        resp = llm.complete(messages, tools=list(tools))
        if resp.stop_reason == "end_turn":
            return resp.content
        if step == max_steps - 1:
            break
        for tc in resp.tool_calls:
            try:
                result = tools[tc.name](**tc.arguments) if tc.name in tools else "error: unknown tool " + tc.name
            except ToolError as e:
                result = "error: " + str(e)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    return "STOPPED: max_steps reached"
