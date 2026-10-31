import json

INFO = {"name": "orders-mcp", "version": "1.4.0"}

TOOLS = [
    {"name": "get_order_status", "description": "Look up the shipping status of an order.",
     "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
     "reply": "Order {order_id} shipped on 2026-10-28 via UPS."},
    {"name": "refund_order", "description": "Refund an order to the original payment method.",
     "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}, "amount_cents": {"type": "integer"}},
                     "required": ["order_id", "amount_cents"]},
     "raise": "Payment provider declined refund for {order_id}: charge is older than 180 days"},
    {"name": "list_warehouses", "description": "List active warehouses.",
     "inputSchema": {"type": "object", "properties": {}},
     "reply": "AUS-1, DFW-2, SEA-1"},
]


def rpc(method, id_=None, params=None, **extra):
    m = {"jsonrpc": "2.0", "method": method}
    if id_ is not None:
        m["id"] = id_
    if params is not None:
        m["params"] = params
    m.update(extra)
    return m


def raw(*msgs):
    return [m if isinstance(m, str) else json.dumps(m) for m in msgs]


INIT = rpc("initialize", 1, {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "claude-desktop", "version": "0.9"}})
INITED = rpc("notifications/initialized")


def case(name, messages, hidden=True, explanation=None, tools=TOOLS):
    c = {"name": name, "hidden": hidden, "args": {"server_info": INFO, "tools": tools, "messages": raw(*messages)}}
    if explanation:
        c["explanation"] = explanation
    return c


def cases():
    return [
        case("Example 1", [INIT, INITED, rpc("tools/list", 2)], hidden=False,
             explanation="The handshake: initialize echoes the supported protocol version, the initialized notification gets no reply (None), "
                         "and tools/list returns name, description and inputSchema for each tool, without the handler."),
        case("Example 2", [rpc("tools/call", 3, {"name": "get_order_status", "arguments": {"order_id": "A-1042"}}),
                           rpc("tools/call", 4, {"name": "refund_order", "arguments": {"order_id": "A-0007", "amount_cents": 4599}})],
             hidden=False,
             explanation="Both calls run their handler. The refund handler raises, and that comes back as a normal result with isError: true "
                         "and the failure text, so the model can tell the customer. It is not a JSON-RPC error."),
        case("Example 3", ['{"jsonrpc": "2.0", "method": "tools/list", "id": 5',
                           rpc("resources/list", 6),
                           rpc("tools/call", "req-7", {"name": "cancel_order", "arguments": {"order_id": "A-1042"}})],
             hidden=False,
             explanation="Truncated JSON is a parse error with id null. resources/list isn't implemented (-32601). An unknown tool name is "
                         "-32602 Invalid params, and the string id \"req-7\" is echoed as a string."),
        case("batch mixed", [INIT, json.dumps([
            rpc("tools/call", 10, {"name": "get_order_status", "arguments": {"order_id": "B-2201"}}),
            rpc("notifications/progress", params={"progressToken": "t1", "progress": 50}),
            rpc("ping", 11),
            {"jsonrpc": "2.0", "id": 12},
            rpc("tools/list", "x-13"),
        ])]),
        case("batch of only notifications", [INIT, json.dumps([INITED, rpc("notifications/cancelled", params={"requestId": 1})])]),
        case("empty batch", ["[]", rpc("ping", 2)]),
        case("notification never runs a tool", [INIT, INITED,
            rpc("tools/call", params={"name": "refund_order", "arguments": {"order_id": "A-9", "amount_cents": 100}}),
            rpc("tools/call", params={"name": "get_order_status", "arguments": {"order_id": "A-9"}}),
            rpc("unknown/notification")]),
        case("invalid requests", [
            json.dumps({"jsonrpc": "1.0", "method": "ping", "id": 1}),
            json.dumps({"jsonrpc": "2.0", "method": 42, "id": 2}),
            json.dumps({"jsonrpc": "2.0", "method": "ping", "id": True}),
            json.dumps({"jsonrpc": "2.0", "method": "ping", "id": None}),
            json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 3, "params": ["x"]}),
            json.dumps({"method": "ping"}),
            "7",
            json.dumps([1, "two", rpc("ping", 9)]),
        ]),
        case("protocol version negotiation", [
            rpc("initialize", 1, {"protocolVersion": "2024-11-05", "capabilities": {}}),
            rpc("initialize", 2, {"protocolVersion": "2099-01-01", "capabilities": {}}),
            rpc("initialize", 3, {"capabilities": {}}),
            rpc("initialize", 4),
        ]),
        case("tools/call params errors", [INIT,
            rpc("tools/call", 20, {"name": "refund_order", "arguments": {"order_id": "A-1"}}),
            rpc("tools/call", 21, {"name": "get_order_status", "arguments": "A-1"}),
            rpc("tools/call", 22, {"arguments": {"order_id": "A-1"}}),
            rpc("tools/call", 23),
            rpc("tools/call", 24, {"name": "list_warehouses"}),
            rpc("tools/call", 25, {"name": "get_order_status", "arguments": {"order_id": "Z-77", "verbose": True}}),
        ]),
        case("whitespace and id zero", ['  {"jsonrpc":"2.0","id":0,"method":"ping"}\n', "not json at all",
                                        rpc("tools/call", -5, {"name": "list_warehouses", "arguments": {}})]),
    ]
