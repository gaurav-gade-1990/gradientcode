## 1. What the problem is really asking

An MCP server is a JSON-RPC 2.0 server with a handful of methods. Claude Desktop (or your own agent) sends it a line of text, and the server sends a line back, or stays silent. All of MCP's tool use rides on that: `initialize` to shake hands, `tools/list` so the model knows what exists, `tools/call` to run one.

Strip the story and this is a **layered dispatcher**. Each layer has one job and its own error code:

```
raw text -> parse (-32700) -> batch split -> envelope check (-32600)
         -> notification? (silence) -> method table (-32601) -> params check (-32602) -> handler
```

The judge feeds your `McpServer` a session of raw messages. For each one it records what `handle` returned (parsed back into JSON, or `None`), and it records every handler call in `tool_runs`. So two things are graded: the exact response shapes, *and* which tools actually ran. Running a tool you should have skipped fails a case even if every response looks right.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `server_info` | `{"name": "orders-mcp", "version": "1.4.0"}` | echoed as `serverInfo` in the `initialize` result |
| `tools` | list of `{"name", "description", "inputSchema", "handler"}` | index by name for `tools/call`; keep the list order for `tools/list` |
| `handler(arguments)` | returns a string or raises (here a `ToolError`) | call it once per valid `tools/call` request |
| `raw` | one message as **text** | `json.loads` it yourself |
| return value | a `str` from `json.dumps`, or `None` | `None` means "send nothing back" |

Three details are easy to miss:

- **A notification is a valid message with no `"id"` key.** Not `id: null` (that is an Invalid Request), and not `id: 0` (that is a perfectly good id). Test with `"id" not in msg`.
- **Python's `bool` is an `int`.** `isinstance(True, int)` is `True`, but this server's ids are strings or integers. `{"id": true}` is an Invalid Request, and so is a fractional id like `1.5` (JSON-RPC discourages them, and the problem only allows integers).
- **A tool that raises is a success at the protocol level.** It becomes `result` with `isError: true`. Only a bad *request* (unknown tool, missing required argument, non-dict arguments) is a `-32602` error.

## 3. Trace the examples by hand

**Example 1**, the handshake: `[INIT, INITED, tools/list id 2]`.

| message | layer that decides | response |
|---|---|---|
| `initialize`, id 1, `protocolVersion: "2025-03-26"` | method table → `_initialize` | `result: {protocolVersion: "2025-03-26", capabilities: {tools: {listChanged: false}}, serverInfo: {...}}` |
| `notifications/initialized`, no id | notification check | `None` |
| `tools/list`, id 2 | method table → `_list` | `result: {tools: [3 entries of name, description, inputSchema]}` |

The second response is `None`, and `tool_runs` is `[]`. The listed tools have no `handler` key: a Python function can't be serialized anyway, and it is not part of the protocol.

**Example 2**, two `tools/call` requests. Both pass the params check (`order_id` present for the first; `order_id` and `amount_cents` for the second), so both handlers run, and `tool_runs` has two entries. The second handler raises `ToolError("Payment provider declined refund for A-0007: charge is older than 180 days")`. The response is still a `result`:

```python
{"jsonrpc": "2.0", "id": 4, "result": {
    "content": [{"type": "text", "text": "Payment provider declined refund for A-0007: charge is older than 180 days"}],
    "isError": True}}
```

**Example 3**, three different failures:

| raw | what happens | response |
|---|---|---|
| `'{"jsonrpc": "2.0", "method": "tools/list", "id": 5'` (truncated) | `json.loads` raises | `-32700 Parse error`, `id: null`. You couldn't read the id, so you can't echo it |
| `resources/list`, id 6 | valid envelope, not in the method table | `-32601 Method not found`, id 6 |
| `tools/call`, id `"req-7"`, name `cancel_order` | valid envelope, method exists, tool doesn't | `-32602 Invalid params`, id `"req-7"` (still a string) |

**The hidden case that teaches the most, "batch mixed":** after `initialize`, one raw message is a JSON array of five elements.

| element | decision | kept in output? |
|---|---|---|
| `tools/call` id 10, `get_order_status B-2201` | runs the handler | yes, `result` with the shipping text |
| `notifications/progress`, no id | notification | no |
| `ping` id 11 | method table | yes, `result: {}` |
| `{"jsonrpc": "2.0", "id": 12}` | no `method`: invalid envelope | yes, `-32600` with id 12 (the id itself is valid, so you echo it) |
| `tools/list` id `"x-13"` | method table | yes |

The response is a JSON array of four objects, in element order. If every element had been a notification ("batch of only notifications"), the list would be empty, and the right answer is `None`, not `"[]"`.

## 4. Key idea: protocol errors vs tool errors

There are two kinds of failure, and they go to different places.

| failure | who caused it | where it goes |
|---|---|---|
| bad JSON, bad envelope, unknown method | the client or SDK | `error` with `-32700`, `-32600`, `-32601` |
| unknown tool, missing required argument, `arguments` not a dict | the caller, before any work started | `error` with `-32602` |
| the handler raised | the request was fine, the work failed | `result` with `isError: true` and the exception text |

The reason is the model. A host usually shows a protocol error as a generic failure, and the model never sees the words. A tool result with `isError: true` goes back to the model as content: it can read "charge is older than 180 days", tell the customer, and try something else. If you turned the exception into `-32603 Internal error`, the model would learn nothing.

## 5. Key idea: a notification is silent and inert

JSON-RPC says a message without an id gets no response, ever. That includes errors: an unknown method in a notification is still silence ("notification never runs a tool" ends with `unknown/notification`, which returns `None`). This problem adds a stricter rule: nothing is executed either, not even a `tools/call`. A `tools/call` without an id is almost always a client bug, and if the client retries it properly with an id, a refund would run twice.

Order matters here. The envelope check runs **before** the notification check. `{"method": "ping"}` (no `jsonrpc`, no id) is not a valid notification. It's an Invalid Request, answered with `id: null`. Only a message that passes the envelope check and has no id is treated as a notification.

## 6. Plan before you code

```
handle(raw):
    try json.loads(raw)            except -> -32700, id null
    if list:
        empty  -> one -32600 object, id null
        else   -> [one(m) for m in list], drop Nones; None if nothing left
    else -> one(msg), or None

one(msg):
    envelope invalid -> -32600, id echoed only if it is a valid id
    no "id" key      -> None (don't execute)
    method not in table -> -32601
    run the method; _InvalidParams -> -32602
    wrap the result
```

And the method table:

| method | params check | result |
|---|---|---|
| `initialize` | `protocolVersion` is a string | version echoed if supported, else `"2025-03-26"` |
| `ping` | none | `{}` |
| `tools/list` | none | `{"tools": [...]}` in registration order |
| `tools/call` | name is a registered string, arguments a dict, required keys present | `content` + `isError` |

## 7. Build it one piece at a time

**Step 1: helpers for ids and errors.** `_valid_id` rules out bools explicitly; `_error` builds the one error shape so every code path matches it.

```python
def _valid_id(x):
    return isinstance(x, str) or (isinstance(x, int) and not isinstance(x, bool))


def _error(id_, code):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": MESSAGES[code]}}
```

**Step 2: parse and split batches in `handle`.** `json.loads` tolerates surrounding whitespace, so `'  {"jsonrpc":"2.0","id":0,"method":"ping"}\n'` parses fine. A failed parse raises `json.JSONDecodeError`, a subclass of `ValueError`.

```python
    def handle(self, raw):
        try:
            msg = json.loads(raw)
        except ValueError:
            return json.dumps(_error(None, -32700))
        if isinstance(msg, list):
            if not msg:
                return json.dumps(_error(None, -32600))
            out = [r for r in (self._one(m) for m in msg) if r is not None]
            return json.dumps(out) if out else None
        r = self._one(msg)
        return None if r is None else json.dumps(r)
```

**Step 3: the envelope check, then the notification check.** The Invalid Request branch echoes the id only when it is a valid one, so `{"id": true}` and `[1, "two", ...]` both get `id: null`.

```python
    def _one(self, msg):
        if not (isinstance(msg, dict) and msg.get("jsonrpc") == "2.0" and isinstance(msg.get("method"), str)
                and ("id" not in msg or _valid_id(msg["id"]))
                and ("params" not in msg or isinstance(msg["params"], dict))):
            id_ = msg.get("id") if isinstance(msg, dict) and _valid_id(msg.get("id")) else None
            return _error(id_, -32600)
        if "id" not in msg:
            return None
```

`if not msg.get("id")` looks equivalent, but it treats `id: 0` as a notification. "whitespace and id zero" catches exactly that.

**Step 4: dispatch.** A dict of bound methods keeps unknown methods to one line. Each method raises `_InvalidParams` for a bad `params`, and `_one` turns that into `-32602`.

```python
        id_, params = msg["id"], msg.get("params", {})
        handler = {"initialize": self._initialize, "ping": lambda p: {},
                   "tools/list": self._list, "tools/call": self._call}.get(msg["method"])
        if handler is None:
            return _error(id_, -32601)
        try:
            return {"jsonrpc": "2.0", "id": id_, "result": handler(params)}
        except _InvalidParams:
            return _error(id_, -32602)
```

**Step 5: `tools/call`.** All the protocol checks come first, so a bad request never reaches the handler. Then the handler's exception is caught broadly (`Exception`, not just `ToolError`): any failure inside the tool is a tool outcome, not a server crash.

```python
    def _call(self, params):
        name, args = params.get("name"), params.get("arguments", {})
        if not isinstance(name, str) or name not in self.tools or not isinstance(args, dict):
            raise _InvalidParams()
        tool = self.tools[name]
        if any(k not in args for k in tool["inputSchema"].get("required", [])):
            raise _InvalidParams()
        try:
            text, is_error = tool["handler"](args), False
        except Exception as e:
            text, is_error = str(e), True
        return {"content": [{"type": "text", "text": text}], "isError": is_error}
```

Only `required` is checked. An extra key like `verbose: true` passes through to the handler (id 25 in "tools/call params errors"); full schema validation is problem 113's job.

## 8. Full solution

```python
import json  # parse incoming text and serialize every reply

# protocol versions this server can speak; the first is the fallback
SUPPORTED_VERSIONS = ("2025-03-26", "2024-11-05")
# the exact error messages the spec requires for each JSON-RPC code
MESSAGES = {-32700: "Parse error", -32600: "Invalid Request", -32601: "Method not found", -32602: "Invalid params"}


def _valid_id(x):  # JSON-RPC ids here are strings or integers
    return isinstance(x, str) or (isinstance(x, int) and not isinstance(x, bool))  # True is an int in Python, so exclude bools


def _error(id_, code):  # one place that builds the error shape, so every path matches it
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": MESSAGES[code]}}  # no data field


class _InvalidParams(Exception):  # raised by a method when its params are wrong, mapped to -32602
    pass  # only the type matters


class McpServer:  # one server instance per connection
    def __init__(self, server_info, tools):  # register the tools once at startup
        self.server_info = server_info  # echoed back in initialize
        self.tools = {t["name"]: t for t in tools}  # look tools up by name for tools/call
        self.order = [t["name"] for t in tools]  # tools/list must keep registration order

    def handle(self, raw):  # one raw message in, response text or None out
        try:  # the text might not be JSON at all
            msg = json.loads(raw)  # tolerates surrounding whitespace and newlines
        except ValueError:  # JSONDecodeError is a ValueError
            return json.dumps(_error(None, -32700))  # we couldn't read an id, so it is null
        if isinstance(msg, list):  # a JSON-RPC batch
            if not msg:  # an empty batch is itself invalid
                return json.dumps(_error(None, -32600))  # one error object, not an array
            out = [r for r in (self._one(m) for m in msg) if r is not None]  # handle each element, drop notifications
            return json.dumps(out) if out else None  # an all-notification batch sends nothing at all
        r = self._one(msg)  # a single message
        return None if r is None else json.dumps(r)  # None means stay silent

    def _one(self, msg):  # handle one request object and return a response dict or None
        # the envelope: a dict, jsonrpc 2.0, a string method, a valid id if any, dict params if any
        if not (isinstance(msg, dict) and msg.get("jsonrpc") == "2.0" and isinstance(msg.get("method"), str)
                and ("id" not in msg or _valid_id(msg["id"]))
                and ("params" not in msg or isinstance(msg["params"], dict))):
            id_ = msg.get("id") if isinstance(msg, dict) and _valid_id(msg.get("id")) else None  # echo the id only if it is usable
            return _error(id_, -32600)  # bad envelope, answered even without an id
        if "id" not in msg:  # a valid message with no id key is a notification (id 0 is still a request)
            return None  # notification: never answered, never executed
        id_, params = msg["id"], msg.get("params", {})  # echo the id as-is; params default to empty
        # method table: each entry takes params and returns the result dict
        handler = {"initialize": self._initialize, "ping": lambda p: {},
                   "tools/list": self._list, "tools/call": self._call}.get(msg["method"])
        if handler is None:  # a method this server doesn't implement
            return _error(id_, -32601)  # method not found
        try:  # methods signal bad params by raising
            return {"jsonrpc": "2.0", "id": id_, "result": handler(params)}  # success wraps whatever the method returned
        except _InvalidParams:  # the request itself was wrong
            return _error(id_, -32602)  # invalid params, a protocol error

    def _initialize(self, params):  # the handshake
        v = params.get("protocolVersion")  # the version the client wants
        if not isinstance(v, str):  # missing or not a string
            raise _InvalidParams()  # can't negotiate without it
        # echo a supported version, otherwise offer our newest one
        return {"protocolVersion": v if v in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": self.server_info}

    def _list(self, params):  # describe the tools to the model, never exposing the handler
        return {"tools": [{k: self.tools[n][k] for k in ("name", "description", "inputSchema")} for n in self.order]}  # in order

    def _call(self, params):  # run one tool after the protocol checks pass
        name, args = params.get("name"), params.get("arguments", {})  # arguments default to an empty object
        if not isinstance(name, str) or name not in self.tools or not isinstance(args, dict):  # unknown tool or bad args
            raise _InvalidParams()  # a client bug, so a protocol error, not tool content
        tool = self.tools[name]  # the registered tool
        if any(k not in args for k in tool["inputSchema"].get("required", [])):  # a required argument is missing
            raise _InvalidParams()  # reject before the handler runs
        try:  # the tool itself may fail
            text, is_error = tool["handler"](args), False  # run it exactly once
        except Exception as e:  # any tool failure is a tool outcome the model should read
            text, is_error = str(e), True  # keep the failure text for the model
        return {"content": [{"type": "text", "text": text}], "isError": is_error}  # success or failure, both are results
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | initialize result, `None`, tool list | the handshake; the initialized notification is silent; `tools/list` has no handler |
| Example 2 | two results, the second with `isError: true`; 2 tool runs | a raising tool is a result, not an error |
| Example 3 | `-32700` id null, `-32601` id 6, `-32602` id `"req-7"` | parse errors; unknown method; unknown tool is a protocol error; string ids stay strings |
| batch mixed | one array of 4 responses | batch splitting, dropping notifications, an Invalid Request inside a batch keeps its id |
| batch of only notifications | `None` for the batch | nothing to send means `None`, not `"[]"` |
| empty batch | one `-32600` object, then the ping works | `[]` is a single error, and the server keeps going |
| notification never runs a tool | four `None`s after initialize, `tool_runs: []` | no reply and no execution for id-less messages, even unknown methods |
| invalid requests | eight `-32600`s, the last inside a batch with a ping result | each envelope rule, bool id, null id, non-dict params, non-object messages |
| protocol version negotiation | `"2024-11-05"` echoed, `"2025-03-26"` fallback, two `-32602`s | version echo and fallback; missing `protocolVersion` or missing params |
| tools/call params errors | four `-32602`s, then two results | missing required key, non-dict args, no name, no params; default `{}` arguments; extra keys allowed |
| fractional id is invalid | two `-32600`s with id null, then the ping result; `tool_runs: []` | a `float` id is not a valid id, and its `tools/call` never runs |
| whitespace and id zero | ping result with id 0, parse error, result with id -5 | `"id" not in msg`, not a falsy check; whitespace around JSON |

## 10. Complexity

Each message costs O(size of the message) to parse and serialize, plus O(1) for the dispatch lookup and O(r) for `r` required keys. `tools/list` is O(T) for `T` tools. A batch of `b` elements is `b` independent messages. Memory is the parsed message plus the response.

In production, the dispatcher is never the bottleneck. The handlers are: a tool call might take seconds. Real servers run requests concurrently and must match responses to requests by id, which is why echoing the id with its exact type (`"req-7"` stays a string, `0` stays `0`) matters so much. A proxy that turns `1` into `"1"` breaks that matching.

## 11. If you got Wrong Answer

- **Example 1's second response is `{"id": null, "result": {}}` instead of `None`.** You're answering notifications. Return `None` when there is no `"id"` key.
- **"notification never runs a tool" has entries in `tool_runs`.** You return `None` for notifications only *after* dispatching. Check for the id before the method table.
- **"batch of only notifications" gives `[]`.** Return `None` when the filtered batch list is empty.
- **"invalid requests" has `{"id": true, "result": {}}`.** Your id check accepts bools. Exclude `bool` explicitly.
- **"fractional id is invalid" answers `{"id": 1.5, "result": {}}` or runs `get_order_status`.** Your id check accepts any number (`wrong_float_id_accepted.py`). Test for `int`, not `(int, float)`.
- **Example 2's refund is `-32603 Internal error`.** A tool exception belongs in `result` with `isError: true`.
- **Example 3's `cancel_order` comes back as a result with `isError: true`.** An unknown tool is `-32602`, not a tool outcome.
- **"whitespace and id zero" gives `None` for the ping.** You wrote `if not msg.get("id")`, which treats `0` as missing.
- **Runtime Error with `ToolError` in the traceback.** You caught too narrow an exception (or none) around the handler. Catch `Exception`.

## 12. Follow-ups an interviewer might ask

- *How would you validate arguments fully, not just `required`?* Run the validator from problem 113 (tool-args-schema-validation) on `arguments` against `inputSchema` before the handler, and return `-32602` when it finds errors.
- *Newer MCP revisions removed batching. What changes?* The `2025-06-18` revision dropped JSON-RPC batches. Negotiate the version in `initialize`, store it, and reject arrays with `-32600` when the session negotiated a version without batching.
- *How do you stop a tool from being called by a client that shouldn't?* Check scopes after validation and before execution (problem 117, tool-permission-scopes). Remote servers sit behind OAuth 2.1 (problem 120).
- *What if a handler is slow?* Run requests concurrently, keyed by id, and honour `notifications/cancelled` by cancelling the matching task. The client already handles responses arriving out of order, because it matches them by id.
- *What would you log?* One span per request: id, method, tool name, duration and `isError`. Those spans feed latency analysis like problem 112 (trace-critical-path).
