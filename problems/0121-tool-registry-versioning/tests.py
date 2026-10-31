def reg(name, version, status="active"):
    return {"op": "register", "name": name, "version": version, "status": status}


def res(spec):
    return {"op": "resolve", "spec": spec}


CRM = [
    reg("crm_lookup", "1.2.0"),
    reg("crm_lookup", "1.4.2"),
    reg("crm_lookup", "1.9.0"),
    reg("crm_lookup", "1.10.0", "deprecated"),
    reg("crm_lookup", "2.0.0"),
]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"ops": CRM + [res("crm_lookup@^1.2"), res("crm_lookup@~1.4"), res("crm_lookup")]},
         "explanation": "^1.2 is [1.2.0, 2.0.0). 1.10.0 is the highest in range but deprecated, so the highest active one, 1.9.0, wins. "
                        "~1.4 is [1.4.0, 1.5.0) and gives 1.4.2. A bare name matches every version, so 2.0.0."},
        {"name": "Example 2", "hidden": False,
         "args": {"ops": [reg("pdf_render", "0.3.1"), reg("pdf_render", "0.4.0"), reg("pdf_render", "0.3.4", "deprecated"),
                          res("pdf_render@^0.3"), reg("pdf_render", "0.3.1", "deprecated"), res("pdf_render@^0.3"),
                          reg("pdf_render", "0.3.1", "removed"), reg("pdf_render", "0.3.4", "removed"), res("pdf_render@^0.3")]},
         "explanation": "^0.3 is [0.3.0, 0.4.0), so 0.4.0 is out. First 0.3.1 is the only active match. After 0.3.1 is deprecated, "
                        "the highest deprecated match, 0.3.4, comes with a warning. Once both are removed the result is the error removed."},
        {"name": "Example 3", "hidden": False,
         "args": {"ops": CRM + [res("crm_lookup@3"), res("jira_search@^1"), res("crm_lookup@>=1.0")]},
         "explanation": "Nothing is in [3.0.0, 4.0.0): not_found. jira_search was never registered: unknown_tool. >=1.0 is not in the grammar: invalid_spec."},
        {"name": "numeric not string order", "args": {"ops": [
            reg("sql_query", "1.9.0"), reg("sql_query", "1.10.0"), reg("sql_query", "1.2.0"),
            res("sql_query@^1"), res("sql_query"), res("sql_query@1"), res("sql_query@~1.9")]}},
        {"name": "caret on zero major", "args": {"ops": [
            reg("vector_upsert", "0.3.0"), reg("vector_upsert", "0.3.7"), reg("vector_upsert", "0.4.2"), reg("vector_upsert", "0.0.3"),
            reg("vector_upsert", "0.0.4"), reg("vector_upsert", "1.0.0"),
            res("vector_upsert@^0.3"), res("vector_upsert@^0.0.3"), res("vector_upsert@^0.0"), res("vector_upsert@^0"),
            res("vector_upsert@^0.4.3"), res("vector_upsert@^0.0.5")]}},
        {"name": "active beats higher deprecated", "args": {"ops": [
            reg("send_email", "2.1.0"), reg("send_email", "2.7.0", "deprecated"), reg("send_email", "2.8.1", "deprecated"),
            res("send_email@^2"), res("send_email@^2.7"), res("send_email@2.8"), reg("send_email", "2.8.1"), res("send_email@^2")]}},
        {"name": "removed versus not found", "args": {"ops": [
            reg("charge_card", "3.0.0", "removed"), reg("charge_card", "3.1.0", "removed"), reg("charge_card", "4.0.0"),
            res("charge_card@^3"), res("charge_card@3.0.0"), res("charge_card@3.2.0"), res("charge_card@^4"), res("charge_card@~5")]}},
        {"name": "exact and tilde", "args": {"ops": [
            reg("geo_lookup", "1.2.3"), reg("geo_lookup", "1.2.9"), reg("geo_lookup", "1.3.0"), reg("geo_lookup", "1.0.0"),
            res("geo_lookup@1.2.3"), res("geo_lookup@~1.2.3"), res("geo_lookup@~1.2.4"), res("geo_lookup@~1"), res("geo_lookup@1.2.4"),
            res("geo_lookup@1.2"), res("geo_lookup@^1.2.10")]}},
        {"name": "malformed specs", "args": {"ops": [
            reg("kb_search", "1.0.0"),
            res("kb_search@"), res("@1.0.0"), res("kb_search@1.0.0.0"), res("kb_search@01.0"), res("kb_search@^"),
            res("kb_search@1.x"), res("kb_search@@1"), res("kb search@1"), res("kb_search@ 1"), res("kb_search@~1.0"),
            res("nobody@x"), res("nobody@1")]}},
        {"name": "re-register flips status", "args": {"ops": [
            reg("ticket_create", "1.0.0"), reg("ticket_create", "1.1.0"), res("ticket_create@^1"),
            reg("ticket_create", "1.1.0", "removed"), res("ticket_create@^1"), reg("ticket_create", "1.0.0", "deprecated"),
            res("ticket_create@^1"), reg("ticket_create", "1.1.0", "active"), res("ticket_create@~1.1"), res("Ticket_create")]}},
        {"name": "many versions", "args": {"ops": [reg("logs_search", "%d.%d.%d" % (a, b, c), ["active", "deprecated", "removed"][(a + b + c) % 3])
                                                    for a in range(3) for b in range(12) for c in range(4)]
                                                   + [res("logs_search@^%d.%d" % (a, b)) for a in range(3) for b in range(0, 13, 3)]
                                                   + [res("logs_search@~%d.%d.%d" % (a, b, c)) for a in range(3) for b in (0, 10, 11) for c in (0, 2, 3)]
                                                   + [res("logs_search@^0.0.%d" % c) for c in range(5)]}},
    ]
