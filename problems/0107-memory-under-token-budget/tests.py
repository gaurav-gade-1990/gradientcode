SYS = {"role": "system", "content": "You are Acme's support agent. Be concise."}


def U(t):
    return {"role": "user", "content": t}


def A(t):
    return {"role": "assistant", "content": t}


def CALL(id, name, **args):
    return {"role": "assistant", "content": None, "tool_calls": [{"id": id, "name": name, "arguments": args}]}


def RES(id, t):
    return {"role": "tool", "tool_call_id": id, "content": t}


CHAT = [SYS,
        U("Hi, my desk lamp from order A-1182 flickers."),
        A("Sorry to hear that. Is it the bulb or the switch?"),
        U("The switch, I think."),
        CALL("c1", "get_order", order_id="A-1182"),
        RES("c1", "A-1182: 2x desk lamp, delivered 2026-10-20, $84.00"),
        A("Your order is eligible for a replacement."),
        U("Great, please send one."),
        A("Done. A replacement ships tomorrow.")]

PARALLEL = [SYS,
            U("Compare my two orders A-1 and A-2."),
            {"role": "assistant", "content": "Checking both.", "tool_calls": [
                {"id": "p1", "name": "get_order", "arguments": {"order_id": "A-1"}},
                {"id": "p2", "name": "get_order", "arguments": {"order_id": "A-2"}}]},
            RES("p1", "A-1: chair, $129.00, delivered"),
            RES("p2", "A-2: desk, $310.00, in transit, ETA 2026-11-04"),
            A("A-1 arrived; A-2 is still on the way."),
            U("When exactly will A-2 arrive?"),
            CALL("p3", "track_package", order_id="A-2"),
            RES("p3", "A-2: out for delivery 2026-11-04 by 6pm"),
            A("By 6pm on Nov 4."),
            U("Thanks!")]


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"messages": CHAT, "budget": 200, "keep_last": 2, "reserve": 30},
         "explanation": "Everything fits in 200 - 30 = 170 tokens, so nothing is dropped and summarize is never called."},
        {"name": "Example 2", "hidden": False, "args": {"messages": CHAT, "budget": 120, "keep_last": 2, "reserve": 30},
         "explanation": "The get_order call and its result form one unit. The pinned last two turns plus the system prompt cost 33 tokens. Walking back: 44, then the tool unit gives 81, then \"The switch, I think.\" lands exactly on the 90-token limit (120 - 30) and still fits. The next older turn would make 106, so the walk stops and the first two messages go to summarize."},
        {"name": "Example 3", "hidden": False, "args": {"messages": CHAT, "budget": 40, "keep_last": 1, "reserve": 10},
         "explanation": "Only the system prompt and the final turn fit. The seven older messages, in their original order, are passed to summarize once."},
        {"name": "pinned tail exceeds budget", "args": {"messages": CHAT, "budget": 20, "keep_last": 4, "reserve": 5}},
        {"name": "keep_last covers everything", "args": {"messages": CHAT, "budget": 10, "keep_last": 20, "reserve": 0}},
        {"name": "tool pair kept whole", "args": {"messages": CHAT, "budget": 85, "keep_last": 2, "reserve": 0}},
        {"name": "tool pair too big stops the walk", "args": {"messages": CHAT, "budget": 75, "keep_last": 2, "reserve": 0}},
        {"name": "parallel calls one unit", "args": {"messages": PARALLEL, "budget": 160, "keep_last": 3, "reserve": 20}},
        {"name": "small older turn after a big one is not used", "args": {"messages": PARALLEL, "budget": 115, "keep_last": 2, "reserve": 10}},
        {"name": "reserve changes the cut", "args": {"messages": PARALLEL, "budget": 100, "keep_last": 2, "reserve": 20}},
        {"name": "keep_last zero", "args": {"messages": CHAT, "budget": 60, "keep_last": 0, "reserve": 15}},
        {"name": "only system", "args": {"messages": [SYS], "budget": 50, "keep_last": 3, "reserve": 10}},
    ]
