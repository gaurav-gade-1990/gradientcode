## Approach

The agent loop is a tiny protocol state machine. The model only sees what is in the transcript, so the transcript has to be exactly what the provider's API expects:

1. `user` turn.
2. `assistant` turn carrying `tool_calls`, each with an id.
3. One `tool` message per call, in the same order, each echoing its call's id.
4. Back to the model with the whole transcript.

```python
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
    return "STOPPED: max_steps reached"
```

Tool errors become data. The model is usually good at recovering ("that order doesn't exist, ask the customer"), and it can't recover from an exception that never reaches it.

## Common mistakes

- **Dropping the assistant turn.** Appending tool results without the `tool_calls` message that asked for them. Anthropic and OpenAI both reject this with a 400.
- **Running only the first tool call.** Models emit parallel tool calls; every one needs a result, or the next request is invalid.
- **Wrong `tool_call_id`.** Tagging every result with one id, or with an index. The model then reads the refund policy as the order status.
- **Letting a tool exception escape.** One flaky backend kills the conversation instead of letting the model retry or apologize.
- **Running tools after the last step.** If you will never call the model again, the side effects (an email, a refund) happen with nobody reading the result.

## Production notes

- This is the loop inside the Anthropic tool runner, the OpenAI Agents SDK `Runner`, and LangGraph's prebuilt ReAct agent. Each one also enforces a step or turn limit; a runaway loop costs real money.
- Parallel tool calls are often run concurrently (problem 103, parallel-tool-dag); the results still go back in call order.
- Return tool errors with an explicit flag where the API supports it (`is_error: true` on Anthropic `tool_result`, `isError` in MCP, problem 114).
- Add loop detection (problem 102) and a token budget for the transcript (problem 107) before you ship this to customers.
