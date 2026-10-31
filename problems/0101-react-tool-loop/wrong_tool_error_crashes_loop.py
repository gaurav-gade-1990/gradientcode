def run_agent(llm, tools, user_msg, max_steps):
    # Bug: a tool exception (or an unknown tool name) escapes and kills the whole conversation.
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
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": tools[tc.name](**tc.arguments)})
    return "STOPPED: max_steps reached"
