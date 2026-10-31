Your team is shipping an MCP server that exposes the order-management tools to Claude Desktop and to your in-house agents. The transport hands you one raw JSON-RPC 2.0 message at a time. Write the dispatcher.

Implement `class McpServer`:

- `McpServer(server_info, tools)`. `server_info` is a dict like `{"name": "orders-mcp", "version": "1.4.0"}`. `tools` is a list of `{"name", "description", "inputSchema", "handler"}`, where `handler(arguments)` returns a string or raises an exception.
- `handle(raw)` takes the raw message text and returns the response **text** (a JSON string), or `None` when nothing should be sent back.

**Envelope (JSON-RPC 2.0).**

| situation | response |
|---|---|
| `raw` isn't valid JSON | error `-32700`, `"Parse error"`, `id: null` |
| `raw` is the empty array `[]` | **one** error object `-32600`, `id: null` (not an array) |
| `raw` is a non-empty array (a batch) | handle each element on its own, then return a JSON array of the responses that exist, in element order, or `None` if there are none |
| an element isn't a valid request (below) | error `-32600`, `"Invalid Request"` |
| valid, with no `"id"` key (a notification) | no response, ever. Nothing is executed, not even a `tools/call` |
| valid request, method unknown | error `-32601`, `"Method not found"` |

A message is a **valid request** when it is a dict, `jsonrpc == "2.0"`, `method` is a string, `id` (if present) is a string or an integer (not a bool, not null), and `params` (if present) is a dict. For an Invalid Request error, echo the element's `id` if it is a dict with a valid `id`, and use `null` otherwise.

A success is `{"jsonrpc": "2.0", "id": <same id, same type>, "result": {...}}`. An error is `{"jsonrpc": "2.0", "id": ..., "error": {"code": c, "message": m}}`, with no `data` field. Use the exact messages above, plus `"Invalid params"` for `-32602`.

**Methods** (MCP spec revision `2025-03-26`, which allows JSON-RPC batching).

| method | behavior |
|---|---|
| `initialize` | `params.protocolVersion` must be a string, else `-32602`. Result: `{"protocolVersion": v, "capabilities": {"tools": {"listChanged": false}}, "serverInfo": server_info}`. `v` echoes the client's version if it's one you support (`"2025-03-26"`, `"2024-11-05"`); otherwise it is `"2025-03-26"` |
| `ping` | result `{}` |
| `tools/list` | result `{"tools": [{"name", "description", "inputSchema"}, ...]}` in registration order. Never include the handler |
| `tools/call` | `params.name` must be a string naming a registered tool, `params.arguments` (default `{}`) must be a dict, and every key in the tool's `inputSchema.required` (default `[]`) must be present. Any failure gives `-32602` |

If `tools/call` passes those checks, call `handler(arguments)` once:

- It returns `s`: the result is `{"content": [{"type": "text", "text": s}], "isError": false}`.
- It raises `e`: the result is `{"content": [{"type": "text", "text": str(e)}], "isError": true}`. A tool failure is **not** a protocol error. The model has to see it to recover.

The client sends `notifications/initialized` after `initialize`. Like every notification, it gets no response.

The judge sends a session of raw messages and grades every response (parsed back into JSON) and every handler invocation.

**Constraints**

- At most 30 messages per session, and batches have at most 10 elements.
- Return a `str` from `json.dumps`, or `None`. The key order inside the JSON doesn't matter.
