def req(at, rid, tool, latency=0.1):
    return {"at": at, "id": rid, "tool": tool, "latency": latency}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"requests": [req(0.0, "r1", "salesforce.get_account"), req(0.0, "r2", "salesforce.list_cases"),
                               req(0.0, "r3", "gmail.search")],
                  "expires_at": 0.0, "refresh_outcomes": ["ok"]},
         "explanation": "The token is already expired. All three calls get 401 at t=0.1. r1 starts the only refresh (0.1 to 0.6); "
                        "r2 and r3 wait on that same Task. At 0.6 all three retry with tok_1 and succeed at 0.7."},
        {"name": "Example 2", "hidden": False,
         "args": {"requests": [req(0.0, "r1", "jira.create_issue"), req(0.05, "r2", "jira.get_issue")],
                  "expires_at": 0.0, "refresh_outcomes": ["invalid_grant"]},
         "explanation": "r1's 401 at 0.1 starts the refresh, and r2's 401 at 0.15 joins it. The refresh token was revoked, so at 0.6 "
                        "BadRequestError reaches both callers. Neither retries."},
        {"name": "Example 3", "hidden": False,
         "args": {"requests": [req(0.0, "r1", "slack.post_message"), req(0.0, "r2", "drive.export_pdf", latency=1.0)],
                  "expires_at": 0.05, "refresh_outcomes": ["ok", "ok"]},
         "explanation": "r1 gets 401 at 0.1 and refreshes to tok_1 by 0.6. r2 was sent with tok_0 and its 401 arrives at 1.0, after the refresh. "
                        "The client already holds a different token, so r2 retries with tok_1 and does not refresh again."},
        {"name": "token never expires", "args": {"requests": [req(0.0, "r1", "crm.get"), req(0.2, "r2", "crm.get")],
                                                  "expires_at": 100.0, "refresh_outcomes": []}},
        {"name": "failure then recovery", "args": {
            "requests": [req(0.0, "r1", "hubspot.get_deal"), req(0.0, "r2", "hubspot.get_contact"), req(2.0, "r3", "hubspot.get_deal"),
                         req(2.0, "r4", "hubspot.list_deals")],
            "expires_at": 0.0, "refresh_outcomes": ["invalid_grant", "ok"]}},
        {"name": "expires mid-traffic", "args": {
            "requests": [req(0.0, "a", "github.list_prs"), req(0.5, "b", "github.get_pr"), req(1.2, "c", "github.get_pr"),
                         req(1.25, "d", "github.comment"), req(1.4, "e", "github.comment", latency=0.3), req(1.9, "f", "github.merge")],
            "expires_at": 1.0, "refresh_outcomes": ["ok"]}},
        {"name": "new token also rejected", "args": {
            "requests": [req(0.0, "r1", "zendesk.get_ticket"), req(0.0, "r2", "zendesk.get_ticket")],
            "expires_at": 0.0, "refresh_outcomes": ["ok"], "token_ttl": 0.05}},
        {"name": "two expiry cycles", "args": {
            "requests": [req(0.0, "a", "notion.query"), req(0.1, "b", "notion.query"), req(1.5, "c", "notion.update"),
                         req(1.5, "d", "notion.query"), req(2.6, "e", "notion.query", latency=0.5), req(2.7, "f", "notion.update")],
            "expires_at": 0.0, "refresh_outcomes": ["ok", "ok", "ok"], "refresh_latency": 0.4, "token_ttl": 1.0}},
        {"name": "slow 401 for old token while second refresh runs", "args": {
            "requests": [req(0.0, "a", "sap.get_po"), req(0.0, "b", "sap.get_po", latency=2.0), req(1.0, "c", "sap.get_po")],
            "expires_at": 0.0, "refresh_outcomes": ["ok", "ok"], "refresh_latency": 0.5, "token_ttl": 0.5}},
        {"name": "stale 401s after a failed refresh", "args": {
            "requests": [req(0.0, "a", "box.download"), req(0.0, "b", "box.download", latency=1.5), req(3.0, "c", "box.upload")],
            "expires_at": 0.0, "refresh_outcomes": ["invalid_grant", "ok"]}},
    ]
