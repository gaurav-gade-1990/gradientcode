def T(id, title, *needs):
    return {"id": id, "title": title, "needs": list(needs)}


def W(name, *skills):
    return {"name": name, "skills": list(skills)}


TEAM = [W("writer", "writing", "english"), W("billing", "billing", "sql"), W("analyst", "sql", "charts"),
        W("polyglot", "writing", "english", "spanish")]
ESCALATION = [
    T("t1", "pull invoice history", "sql"),
    T("t2", "refund eligibility check", "billing", "sql"),
    T("t3", "draft apology email", "writing", "english"),
    T("t4", "translate apology to Spanish", "writing", "spanish"),
    T("t5", "chart late deliveries", "sql", "charts"),
    T("t6", "summarize thread", "writing"),
]


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"subtasks": ESCALATION, "workers": TEAM},
         "explanation": "t1 (sql) can go to analyst or billing, both empty, so analyst wins on name. t3 ties polyglot and writer at load 0 and goes to polyglot; t6 then goes to writer (load 0 beats polyglot's 2). Rounds visit analyst, billing, polyglot, writer."},
        {"name": "Example 2", "hidden": False, "args": {"subtasks": ESCALATION[:3] + [T("t7", "file a Jira ticket", "jira")], "workers": TEAM,
                                                         "fail_pairs": [["analyst", "t1"]]},
         "explanation": "analyst fails t1. It goes to the back of billing's queue (billing is the only other sql worker), behind t2, and succeeds there in round 2. Nobody has the jira skill, so t7 is unroutable."},
        {"name": "Example 3", "hidden": False, "args": {"subtasks": [T("t1", "pull invoice history", "sql"), T("t2", "refund eligibility check", "billing", "sql")],
                                                         "workers": TEAM, "down": ["billing"]},
         "explanation": "billing is down. t1 goes to analyst (it wins the tie on name) and succeeds. t2 needs billing and sql, which only billing has. It fails there and no other worker is eligible, so t2 is failed after 1 attempt."},
        {"name": "everyone eligible, balance by load", "args": {"subtasks": [T("s%d" % i, "summarize doc %d" % i, "writing") for i in range(1, 8)],
                                                               "workers": [W("wren", "writing"), W("ada", "writing"), W("milo", "writing")]}},
        {"name": "needs all tags, not any", "args": {"subtasks": [T("t1", "Spanish apology", "writing", "spanish"), T("t2", "English apology", "writing", "english")],
                                                    "workers": [W("aaron", "writing"), W("bea", "spanish"), W("cruz", "writing", "spanish", "english")]}},
        {"name": "second attempt also fails", "args": {"subtasks": [T("t1", "refund calc", "sql"), T("t2", "invoice csv", "sql")],
                                                      "workers": [W("bq", "sql"), W("pg", "sql"), W("duck", "sql")],
                                                      "fail_pairs": [["bq", "t1"], ["pg", "t1"], ["duck", "t2"]]}},
        {"name": "reassign never returns to failing worker", "args": {"subtasks": [T("t1", "draft reply", "writing"), T("t2", "draft reply 2", "writing")],
                                                                     "workers": [W("zed", "writing"), W("amy", "writing")], "fail_pairs": [["amy", "t1"]]}},
        {"name": "reassigned to worker earlier in the round", "args": {
            "subtasks": [T("a1", "chart churn", "charts"), T("a2", "chart refunds", "charts"), T("a3", "chart nps", "charts")],
            "workers": [W("viz", "charts"), W("plot", "charts")], "fail_pairs": [["viz", "a2"]]}},
        {"name": "results in subtask order despite rounds", "args": {
            "subtasks": [T("z9", "long report", "writing"), T("a1", "sql pull", "sql"), T("m5", "another report", "writing"), T("b2", "sql pull 2", "sql")],
            "workers": [W("yara", "writing"), W("abe", "sql")], "fail_pairs": [["yara", "z9"]]}},
        {"name": "all down", "args": {"subtasks": ESCALATION, "workers": TEAM, "down": ["writer", "billing", "analyst", "polyglot"]}},
        {"name": "no needs means anyone", "args": {"subtasks": [T("n1", "say hello"), T("n2", "say bye"), T("n3", "ack")],
                                                  "workers": [W("echo"), W("bravo", "sql")]}},
    ]
