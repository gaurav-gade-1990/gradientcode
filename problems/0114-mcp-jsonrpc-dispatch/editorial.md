## Approach

Handle the message in layers, and give each layer one job:

1. **Parse.** `json.loads` fails: `-32700`, id `null`.
2. **Batch.** `[]`: one `-32600`. A non-empty list: handle each element, keep the non-`None` responses, and return `None` if nothing is left.
3. **Envelope.** `jsonrpc == "2.0"`, a string `method`, a string or int `id` (bool is excluded), and dict `params`. Failing any of these is `-32600`.
4. **Notification.** There is no `id` key, so return `None`. Nothing runs.
5. **Dispatch.** Look the method up in a table. A missing method is `-32601`. Each handler raises `_InvalidParams` for `-32602` and otherwise returns the `result`.

```python
def _call(self, params):
    name, args = params.get("name"), params.get("arguments", {})
    if not isinstance(name, str) or name not in self.tools or not isinstance(args, dict):
        raise _InvalidParams()
    if any(k not in args for k in self.tools[name]["inputSchema"].get("required", [])):
        raise _InvalidParams()
    try:
        text, is_error = self.tools[name]["handler"](args), False
    except Exception as e:
        text, is_error = str(e), True
    return {"content": [{"type": "text", "text": text}], "isError": is_error}
```

The key split is between **protocol errors** and **tool errors**. A protocol error means the request itself was wrong: the client or SDK sent garbage, called a method that doesn't exist, or named a tool that doesn't exist. A tool error means the request was fine and the work failed. The model can't act on a protocol error, which the host usually shows as a generic failure. It can act on `isError: true` content: apologize, try another order id, or escalate.

## Common mistakes

- **A tool exception as `-32603`.** The model sees "Internal error" instead of "charge is older than 180 days" and retries blindly. MCP's spec says tool execution errors go in the result with `isError: true`.
- **Answering notifications.** The client never sent an id, so a `{"id": null, ...}` reply looks like an orphan response. Some clients log it as a protocol violation and drop the connection.
- **Executing a `tools/call` that has no id.** Nobody will ever see the result, and if the client retries properly, the refund runs twice.
- **`[]` for an all-notification batch.** JSON-RPC says to return nothing at all.
- **Unknown tool as `isError` content.** MCP lists unknown tools under protocol errors (`-32602`). It's a client bug, not a tool outcome.
- **`isinstance(True, int)`.** In Python a bool passes as an int, but JSON-RPC ids are strings or numbers.

## Production notes

- Use the official SDKs (`mcp` for Python, `@modelcontextprotocol/sdk` for TypeScript), which do this framing for you. Still, you need to know the shapes when you debug a stdio server that writes logs to stdout and corrupts the stream, or a proxy that rewrites ids.
- MCP's `2025-06-18` revision **removed** JSON-RPC batching, so newer servers reject arrays. Negotiate the version in `initialize` and gate the behavior on it.
- Add `tools/list` pagination (`cursor` / `nextCursor`), `notifications/tools/list_changed` when tools are hot-reloaded, and `structuredContent` with an `outputSchema` for typed results.
- Validate `arguments` against `inputSchema` (problem 113) and check scopes (problem 117) before the handler runs. Remote MCP servers sit behind OAuth 2.1 (problem 120).
- Log every request id with the tool name, duration and `isError`. Those spans are what you'll debug from (problem 112).
