TOOLS = {
    "get_order": [
        {"args": {"order_id": "A-1182"}, "result": "order A-1182: 2x desk lamp, delivered 2026-10-20, total $84.00"},
        {"args": {"order_id": "A-2001"}, "result": "order A-2001: 1x office chair, in transit"},
        {"args": {"order_id": "A-0000"}, "error": "order A-0000 not found"},
    ],
    "get_refund_policy": [
        {"args": {"category": "lighting"}, "result": "lighting: refundable within 30 days of delivery"},
        {"args": {}, "result": "default: refundable within 14 days of delivery"},
    ],
}
ORDER = {"tool_calls": [{"name": "get_order", "arguments": {"order_id": "A-1182"}}]}
POLICY = {"tool_calls": [{"name": "get_refund_policy", "arguments": {"category": "lighting"}}]}
DONE = {"content": "Order A-1182 was delivered on Oct 20, so it is still inside the 30-day refund window."}
Q = "Can I still return the lamps from order A-1182?"


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"script": [ORDER, DONE], "tool_table": TOOLS, "user_msg": Q, "max_steps": 5},
         "explanation": "Call 1 sends only the user turn. The model asks for get_order, so call 2 sends the user turn, the assistant turn with its tool_calls, and the tool result tagged with tool_call_id call_1. The model then answers."},
        {"name": "Example 2", "hidden": False,
         "args": {"script": [{"content": "Let me check both.", "tool_calls": [
             {"name": "get_order", "arguments": {"order_id": "A-1182"}},
             {"name": "get_refund_policy", "arguments": {"category": "lighting"}}]}, DONE],
             "tool_table": TOOLS, "user_msg": Q, "max_steps": 5},
         "explanation": "Two tool calls in one response. Both run in order, and each tool message carries its own id (call_1, then call_2)."},
        {"name": "Example 3", "hidden": False,
         "args": {"script": [{"tool_calls": [{"name": "get_order", "arguments": {"order_id": "A-0000"}}]},
                             {"content": "I could not find order A-0000. Can you double-check the number?"}],
                  "tool_table": TOOLS, "user_msg": "Where is order A-0000?", "max_steps": 5},
         "explanation": "The tool raises ToolError. The loop does not crash: it sends \"error: order A-0000 not found\" back as the tool result."},
        {"name": "answers immediately", "args": {"script": [{"content": "Happy to help. What is your order number?"}],
                                                  "tool_table": TOOLS, "user_msg": "I need help with a return", "max_steps": 3}},
        {"name": "max steps hit, last tools not run", "args": {"script": [ORDER, POLICY, ORDER, DONE], "tool_table": TOOLS,
                                                               "user_msg": Q, "max_steps": 3}},
        {"name": "max_steps 1 with tool use", "args": {"script": [ORDER, DONE], "tool_table": TOOLS, "user_msg": Q, "max_steps": 1}},
        {"name": "exactly max_steps calls ending in answer", "args": {"script": [ORDER, POLICY, DONE], "tool_table": TOOLS,
                                                                      "user_msg": Q, "max_steps": 3}},
        {"name": "unknown tool", "args": {"script": [{"tool_calls": [{"name": "issue_refund", "arguments": {"order_id": "A-1182"}}]},
                                                     {"content": "I can't issue refunds myself; I've flagged this for a human."}],
                                          "tool_table": TOOLS, "user_msg": "Refund A-1182 now.", "max_steps": 4}},
        {"name": "three parallel calls then chained call", "args": {"script": [
            {"tool_calls": [{"name": "get_order", "arguments": {"order_id": "A-1182"}},
                            {"name": "get_order", "arguments": {"order_id": "A-2001"}},
                            {"name": "get_order", "arguments": {"order_id": "A-0000"}}]},
            {"content": "Checking the policy.", "tool_calls": [{"name": "get_refund_policy", "arguments": {}}]},
            {"content": "A-1182 is delivered, A-2001 is in transit, and A-0000 does not exist."}],
            "tool_table": TOOLS, "user_msg": "Status of A-1182, A-2001 and A-0000?", "max_steps": 6}},
        {"name": "mixed error and success in one turn", "args": {"script": [
            {"tool_calls": [{"name": "lookup_customer", "arguments": {"email": "dana@example.com"}},
                            {"name": "get_order", "arguments": {"order_id": "A-2001"}}]},
            {"content": "Your chair is in transit."}],
            "tool_table": TOOLS, "user_msg": "Where is my chair? I'm dana@example.com", "max_steps": 2}},
        {"name": "explicit ids from model", "args": {"script": [
            {"tool_calls": [{"id": "toolu_01A", "name": "get_order", "arguments": {"order_id": "A-2001"}},
                            {"id": "toolu_01B", "name": "get_refund_policy", "arguments": {}}]},
            {"content": "It is in transit; once delivered you have 14 days."}],
            "tool_table": TOOLS, "user_msg": "Chair order A-2001: can I return it later?", "max_steps": 5}},
    ]
