import json

SUPPORTED_VERSIONS = ("2025-03-26", "2024-11-05")
MESSAGES = {-32700: "Parse error", -32600: "Invalid Request", -32601: "Method not found", -32602: "Invalid params"}


def _valid_id(x):
    return isinstance(x, str) or (isinstance(x, int) and not isinstance(x, bool))


def _error(id_, code):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": MESSAGES[code]}}


class _InvalidParams(Exception):
    pass


class McpServer:
    def __init__(self, server_info, tools):
        self.server_info = server_info
        self.tools = {t["name"]: t for t in tools}
        self.order = [t["name"] for t in tools]

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

    def _one(self, msg):
        if not (isinstance(msg, dict) and msg.get("jsonrpc") == "2.0" and isinstance(msg.get("method"), str)
                and ("id" not in msg or _valid_id(msg["id"]))
                and ("params" not in msg or isinstance(msg["params"], dict))):
            id_ = msg.get("id") if isinstance(msg, dict) and _valid_id(msg.get("id")) else None
            return _error(id_, -32600)
        if "id" not in msg:
            return None  # notification: never answered, never executed
        id_, params = msg["id"], msg.get("params", {})
        handler = {"initialize": self._initialize, "ping": lambda p: {},
                   "tools/list": self._list, "tools/call": self._call}.get(msg["method"])
        if handler is None:
            return _error(id_, -32601)
        try:
            return {"jsonrpc": "2.0", "id": id_, "result": handler(params)}
        except _InvalidParams:
            return _error(id_, -32602)

    def _initialize(self, params):
        v = params.get("protocolVersion")
        if not isinstance(v, str):
            raise _InvalidParams()
        return {"protocolVersion": v if v in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": self.server_info}

    def _list(self, params):
        return {"tools": [{k: self.tools[n][k] for k in ("name", "description", "inputSchema")} for n in self.order]}

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
