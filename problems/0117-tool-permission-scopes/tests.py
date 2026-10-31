ROLES = {
    "support": ["orders:read", "refunds:create", "tickets:*"],
    "support_lead": ["orders:read", "refunds:*", "orders:admin", "tickets:*"],
    "finance": ["refunds:*", "orders:read", "ledger:read"],
    "platform_admin": ["*"],
    "ops": ["orders:*"],
}

COPILOT = {"name": "refund-copilot",
           "allowed_tools": ["get_order", "refund_order", "add_ticket_note", "export_orders"],
           "scopes": ["orders:*", "refunds:create", "tickets:write", "orders_export:run"]}

TOOLS = {
    "get_order": {"scopes": ["orders:read"], "resource_arg": "order_id", "admin_scope": "orders:admin"},
    "refund_order": {"scopes": ["orders:read", "refunds:create"], "resource_arg": "order_id"},
    "add_ticket_note": {"scopes": ["tickets:write"]},
    "export_orders": {"scopes": ["orders_export:run"]},
    "delete_customer": {"scopes": ["customers:delete"], "resource_arg": "customer_id"},
}

RES = {
    "ord_1001": {"tenant": "acme", "owner": "u_maya"},
    "ord_1002": {"tenant": "acme", "owner": "u_omar"},
    "ord_7777": {"tenant": "globex", "owner": "u_maya"},
    "cus_55": {"tenant": "acme", "owner": "u_maya"},
}

MAYA = {"id": "u_maya", "tenant": "acme", "roles": ["support"]}


def call(i, tool, **arguments):
    return {"id": "call_%d" % i, "tool": tool, "arguments": arguments}


def case(name, user, calls, hidden=True, agent=COPILOT, explanation=None):
    c = {"name": name, "hidden": hidden,
         "args": {"user": user, "agent": agent, "role_scopes": ROLES, "tools": TOOLS, "resources": RES, "calls": calls}}
    if explanation:
        c["explanation"] = explanation
    return c


def cases():
    lead = {"id": "u_lena", "tenant": "acme", "roles": ["support_lead"]}
    return [
        case("Example 1", MAYA, [call(1, "get_order", order_id="ord_1001"), call(2, "refund_order", order_id="ord_1001", amount_cents=2500),
                                 call(3, "add_ticket_note", ticket_id="T-88", note="Refund issued")], hidden=False,
             explanation="Maya owns ord_1001. orders:read is effective because her support role grants it exactly and the agent's orders:* "
                         "covers it. tickets:write comes from her tickets:* and the agent's exact grant. All three calls are allowed."),
        case("Example 2", MAYA, [call(1, "get_order", order_id="ord_1002"), call(2, "export_orders", since="2026-10-01"),
                                 call(3, "delete_customer", customer_id="cus_55")], hidden=False,
             explanation="ord_1002 belongs to Omar, and Maya has no orders:admin, so not_owner. The agent may run export_orders, but Maya's "
                         "roles don't grant orders_export:run (and tickets:* doesn't cover it), so missing_scopes. delete_customer isn't in "
                         "the agent's allowed_tools."),
        case("Example 3", lead, [call(1, "get_order", order_id="ord_1002"), call(2, "get_order", order_id="ord_7777"),
                                 call(3, "refund_order", order_id="ord_1002", amount_cents=900)], hidden=False,
             explanation="Lena's orders:admin is effective (the agent has orders:*), so she can read Omar's order. Admin never crosses a "
                         "tenant, so ord_7777 is denied. refund_order has no admin_scope, so the owner check still applies."),
        case("confused deputy: agent broader than user", {"id": "u_kim", "tenant": "acme", "roles": ["finance"]},
             [call(1, "get_order", order_id="ord_1001"), call(2, "add_ticket_note", ticket_id="T-9", note="x"),
              call(3, "refund_order", order_id="ord_1001", amount_cents=100)]),
        case("user broader than agent", {"id": "u_root", "tenant": "acme", "roles": ["platform_admin"]},
             [call(1, "get_order", order_id="ord_1002"), call(2, "export_orders"), call(3, "delete_customer", customer_id="cus_55")],
             agent={"name": "ops-agent", "allowed_tools": ["get_order", "export_orders", "delete_customer"], "scopes": ["orders:read"]}),
        case("wildcard on both sides", {"id": "u_maya", "tenant": "acme", "roles": ["support_lead"]},
             [call(1, "refund_order", order_id="ord_1001", amount_cents=10), call(2, "get_order", order_id="ord_1002")],
             agent={"name": "lead-agent", "allowed_tools": ["get_order", "refund_order"], "scopes": ["orders:*", "refunds:*"]}),
        case("prefix without colon does not match", {"id": "u_ana", "tenant": "acme", "roles": ["ops"]},
             [call(1, "export_orders"), call(2, "get_order", order_id="ord_1001")],
             agent={"name": "ops-agent", "allowed_tools": ["get_order", "export_orders"], "scopes": ["orders:*", "orders_export:run"]}),
        case("resource checks", MAYA, [call(1, "get_order", order_id="ord_9999"), call(2, "get_order"),
                                       call(3, "refund_order", order_id="ord_7777", amount_cents=5),
                                       call(4, "get_order", order_id=1001), call(5, "unknown_tool_x", order_id="ord_1001")]),
        case("missing scopes sorted and unknown role", {"id": "u_new", "tenant": "acme", "roles": ["intern", "contractor"]},
             [call(1, "refund_order", order_id="ord_1001", amount_cents=1), call(2, "add_ticket_note", ticket_id="T-1", note="hi")]),
        case("cross tenant user with admin", {"id": "u_g1", "tenant": "globex", "roles": ["support_lead"]},
             [call(1, "get_order", order_id="ord_1001"), call(2, "get_order", order_id="ord_7777"),
              call(3, "refund_order", order_id="ord_7777", amount_cents=50)]),
    ]
