def S(id, parent, name, kind, start, end):
    return {"id": id, "parent": parent, "name": name, "kind": kind, "start": start, "end": end}


SIMPLE = [
    S("a", None, "POST /chat", "agent", 0, 1000),
    S("b", "a", "claude.messages", "llm", 10, 400),
    S("c", "a", "tool.get_order", "tool", 400, 650),
    S("d", "a", "claude.messages", "llm", 650, 990),
]
PARALLEL = [
    S("root", None, "agent.run", "agent", 0, 2000),
    S("plan", "root", "llm.plan", "llm", 0, 300),
    S("t1", "root", "tool.search_kb", "tool", 300, 900),
    S("t2", "root", "tool.get_customer", "tool", 300, 1400),
    S("t3", "root", "tool.get_orders", "tool", 350, 1100),
    S("db", "t2", "postgres.query", "db", 400, 1300),
    S("ans", "root", "llm.answer", "llm", 1400, 1950),
]


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"spans": SIMPLE},
         "explanation": "The root's children cover 10-990 with no gaps between them, so its self time is 1000 - 980 = 20. The critical path follows the child that ends last: d."},
        {"name": "Example 2", "hidden": False, "args": {"spans": PARALLEL},
         "explanation": "Three tools run in parallel. The root's children cover 0-1950 as one union, so the root's self time is 50, not 2000 minus the sum of the durations. Tool time is the union 300-1400 = 1100 ms."},
        {"name": "Example 3", "hidden": False, "args": {"spans": [
            S("r", None, "agent.run", "agent", 0, 500), S("l", "r", "llm.call", "llm", 20, 480),
            S("x", "gone", "tool.fetch_url", "tool", 100, 300), S("y", "x", "http.get", "http", 110, 290)]},
         "explanation": "Span x's parent was dropped by the sampler, so x and its child y are orphans. They're reported and left out of every other number."},
        {"name": "child outlives parent", "args": {"spans": [
            S("r", None, "agent.run", "agent", 0, 1000), S("tool", "r", "tool.send_email", "tool", 800, 1500),
            S("llm", "r", "llm.call", "llm", 100, 700)]}},
        {"name": "deep chain", "args": {"spans": [
            S("r", None, "agent.run", "agent", 0, 3000), S("s1", "r", "subagent.research", "agent", 100, 2900),
            S("s2", "s1", "llm.call", "llm", 150, 900), S("s3", "s1", "tool.browse", "tool", 900, 2800),
            S("s4", "s3", "http.get", "http", 950, 2000), S("s5", "s3", "llm.extract", "llm", 2000, 2750)]}},
        {"name": "critical path is latest end, not longest", "args": {"spans": [
            S("r", None, "agent.run", "agent", 0, 1000), S("long", "r", "llm.big", "llm", 0, 800),
            S("late", "r", "tool.ping", "tool", 900, 990)]}},
        {"name": "end ties broken by later start then id", "args": {"spans": [
            S("r", None, "agent.run", "agent", 0, 100), S("k2", "r", "tool.a", "tool", 10, 90), S("k1", "r", "tool.b", "tool", 10, 90),
            S("k0", "r", "tool.c", "tool", 0, 90), S("k1a", "k1", "llm.x", "llm", 20, 60)]}},
        {"name": "nested parallel llm calls", "args": {"spans": [
            S("r", None, "agent.run", "agent", 0, 1200),
            S("g", "r", "gather", "agent", 100, 1100),
            S("l1", "g", "llm.call", "llm", 100, 600), S("l2", "g", "llm.call", "llm", 200, 800), S("l3", "g", "llm.call", "llm", 900, 1000),
            S("t", "r", "tool.lookup", "tool", 1100, 1150)]}},
        {"name": "single span", "args": {"spans": [S("only", None, "llm.call", "llm", 5.5, 105.25)]}},
        {"name": "orphan subtree with deep children", "args": {"spans": [
            S("r", None, "agent.run", "agent", 0, 400), S("a1", "r", "llm.call", "llm", 0, 100),
            S("o1", "missing", "tool.x", "tool", 50, 350), S("o2", "o1", "llm.y", "llm", 60, 340), S("o3", "o2", "db.z", "db", 70, 80),
            S("a2", "r", "tool.lookup", "tool", 150, 300)]}},
        {"name": "fractional ms", "args": {"spans": [
            S("r", None, "agent.run", "agent", 0.0, 10.5), S("a", "r", "llm.call", "llm", 0.25, 4.75),
            S("b", "r", "tool.call", "tool", 4.5, 9.125), S("c", "b", "http.get", "http", 5.0, 9.0)]}},
    ]
