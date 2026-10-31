SQL_ERR = "ERROR: relation \"orders_v2\" does not exist (SQLSTATE 42P01)"
JIRA = ("PAY-4821 Refund webhook drops events. Steps: create refund, wait 30s, check ledger. "
        "Expected: ledger row. Actual: none. Comment from Priya: seeing it since the 3.2 deploy.")
LOGS = [
    {"ts": "09:14:02", "level": "ERROR", "msg": "timeout calling payments"},
    {"ts": "09:14:05", "level": "WARN", "msg": "retrying payments"},
    {"ts": "09:14:09", "level": "ERROR", "msg": "circuit open"},
    {"ts": "09:15:00", "level": "INFO", "msg": "recovered"},
]


def _long_ticket(i):
    words = ["customer", "reports", "invoice", "mismatch", "on", "order", "#%d" % (1000 + i), ";", "agent", "escalated",
             "to", "billing", "-", "see", "thread", "(", "v%d.%d" % (i % 4, i % 7), ")", "."]
    return " ".join(words * (3 + i % 5))


def cases():
    big_logs = [{"ts": "10:%02d:%02d" % (i // 60, i % 60), "level": ["INFO", "WARN", "ERROR"][i % 3],
                 "msg": "request %d took %d ms" % (i, 40 + (i * 37) % 900)} for i in range(120)]
    return [
        {"name": "Example 1", "hidden": False, "args": {"results": [
            {"id": "t1", "tool": "jira_get_issue", "type": "text", "content": JIRA},
            {"id": "t2", "tool": "sql_query", "type": "error", "content": SQL_ERR}], "budget": 40},
         "explanation": "The SQL error is 13 tokens and is kept whole, leaving 40 - 13 = 27 for the ticket. The ticket is 41 tokens, "
                        "so keep its first 27 - 5 = 22 tokens (through 'ledger') and append ' [truncated 19 tokens]'. The ticket now costs exactly 27."},
        {"name": "Example 2", "hidden": False, "args": {"results": [
            {"id": "logs", "tool": "log_search", "type": "list", "content": LOGS}], "budget": 60},
         "explanation": "Each log line is a dict counted as sorted JSON: 31, 30, 30 and 29 tokens, 120 in all, over the share of 60. "
                        "Keep items while the sum stays <= 60 - 3 = 57: only the first (31 + 30 = 61 is too many). The cursor is base64('logs:1') = 'bG9nczox' and costs 3, so 34."},
        {"name": "Example 3", "hidden": False, "args": {"results": [
            {"id": "a", "tool": "kb_search", "type": "list", "content": ["Refunds post within 5 days.", "Disputes go to Tier 2."]},
            {"id": "b", "tool": "crm_lookup", "type": "text", "content": "Acme Corp, plan Enterprise, owner Dana."},
            {"id": "c", "tool": "send_email", "type": "error", "content": "SMTP 550: mailbox unavailable"}], "budget": 30},
         "explanation": "The error costs 5, so R = 25 and each of the two other results gets 25 // 2 = 12. The list is 6 + 6 = 12 tokens and the text is 9, "
                        "so both fit whole: no cursor, no marker, 26 tokens in all."},
        {"name": "no non-error results", "args": {"results": [
            {"id": "e1", "tool": "sql_query", "type": "error", "content": SQL_ERR},
            {"id": "e2", "tool": "http_get", "type": "error", "content": "HTTP 503 from inventory-svc after 3 retries; upstream reset."}], "budget": 5}},
        {"name": "errors exceed budget", "args": {"results": [
            {"id": "e", "tool": "sql_query", "type": "error", "content": SQL_ERR},
            {"id": "t", "tool": "jira_get_issue", "type": "text", "content": JIRA},
            {"id": "l", "tool": "log_search", "type": "list", "content": LOGS}], "budget": 10}},
        {"name": "share below marker", "args": {"results": [
            {"id": "t", "tool": "jira_get_issue", "type": "text", "content": JIRA},
            {"id": "u", "tool": "jira_get_issue", "type": "text", "content": "Short note."}], "budget": 7}},
        {"name": "share exactly marker plus one", "args": {"results": [
            {"id": "t", "tool": "jira_get_issue", "type": "text", "content": JIRA}], "budget": 6}},
        {"name": "text exactly fits", "args": {"results": [
            {"id": "t", "tool": "jira_get_issue", "type": "text", "content": JIRA}], "budget": 41}},
        {"name": "text one over", "args": {"results": [
            {"id": "t", "tool": "jira_get_issue", "type": "text", "content": JIRA}], "budget": 40}},
        {"name": "punctuation heavy cut", "args": {"results": [
            {"id": "cfg", "tool": "read_file", "type": "text",
             "content": "retry.max=5; retry.base_ms=250;\n\ttimeouts: {connect: 2s, read: 30s}  # owner: platform-infra"}], "budget": 15}},
        {"name": "big item first blocks smaller later items", "args": {"results": [
            {"id": "hits", "tool": "kb_search", "type": "list", "content": [
                "Refund policy: " + " ".join(["refunds over $500 need manager approval"] * 4),
                "Tier 2 owns disputes.", "SLA is 24h."]}], "budget": 20}},
        {"name": "list cursor with zero items", "args": {"results": [
            {"id": "logs", "tool": "log_search", "type": "list", "content": LOGS}], "budget": 20}},
        {"name": "empty list and empty text", "args": {"results": [
            {"id": "l", "tool": "log_search", "type": "list", "content": []},
            {"id": "t", "tool": "read_file", "type": "text", "content": ""}], "budget": 0}},
        {"name": "many results mixed", "args": {"results": [
            {"id": "r%d" % i, "tool": ["jira_get_issue", "log_search", "sql_query"][i % 3],
             "type": ["text", "list", "error"][i % 3],
             "content": [_long_ticket(i), big_logs[i * 7:i * 7 + 12], "ERROR: deadlock detected on orders (txn %d)" % i][i % 3]}
            for i in range(15)], "budget": 900}},
        {"name": "large log search", "args": {"results": [
            {"id": "q-77", "tool": "log_search", "type": "list", "content": big_logs},
            {"id": "ticket", "tool": "jira_get_issue", "type": "text", "content": _long_ticket(9) * 4}], "budget": 1500}},
    ]
