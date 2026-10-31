Your support agent answers order questions by calling tools such as `get_order` and `get_refund_policy`. Write the core agent loop that sits between the model and the tools.

`run_agent(llm, tools, user_msg, max_steps)` gets:

- `llm`, a `gc_runtime.FakeLLM`. Call `llm.complete(messages, tools=list(tools))`. It returns a `Response` with `.content`, `.tool_calls` (a list of `ToolCall` with `.id`, `.name`, `.arguments`) and `.stop_reason` (`"end_turn"` or `"tool_use"`).
- `tools`, a dict from tool name to a Python function. Call it as `tools[name](**arguments)`. It returns a string or raises `gc_runtime.ToolError`.
- `user_msg`, the customer's message, and `max_steps`, the most model calls you may make.

Keep one transcript, starting with `[{"role": "user", "content": user_msg}]`, and send the whole transcript on every call. After each response:

| response | what to do |
|---|---|
| `stop_reason == "end_turn"` | return `response.content` |
| `stop_reason == "tool_use"` | append `{"role": "assistant", "content": response.content, "tool_calls": [tc.to_dict() for tc in response.tool_calls]}`, then for **each** tool call in order append `{"role": "tool", "tool_call_id": tc.id, "content": result}`, then call the model again |

The tool message's `content` is:

| outcome | content |
|---|---|
| the tool returned `s` | `s` |
| the tool raised `ToolError` `e` | `"error: " + str(e)` |
| `tc.name` is not in `tools` | `"error: unknown tool " + tc.name` (don't call anything) |

A tool error never ends the run. The model sees the error and decides what to do next.

Make at most `max_steps` model calls. If the response to call number `max_steps` still asks for tools, don't run them; return the string `"STOPPED: max_steps reached"`.

The judge records the exact transcript sent on every model call, the tool list you offered, and every tool function call with its arguments.

**Constraints**

- `1 <= max_steps <= 10`
- A response has at most 4 tool calls
- Tool call ids are unique within a run
