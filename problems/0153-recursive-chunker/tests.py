PTO = (
    "PTO Policy\n\n"
    "Full-time employees accrue 1.5 days of paid time off per month. "
    "Accrual starts on the first day of employment.\n\n"
    "Unused PTO carries over up to 10 days. Anything above the cap expires on January 31."
)

RUNBOOK = (
    "Runbook: payments-api 5xx spike\n"
    "1. Check the error budget dashboard for payments-api.\n"
    "2. If the spike started after a deploy, roll back with `deployctl rollback payments-api`.\n"
    "3. Page the on-call DBA if p99 query latency is above 800 ms."
)

LONG_SENTENCE = (
    "Customers on the Enterprise plan may request a dedicated single-tenant deployment in any supported "
    "region including us-east-1 eu-west-1 and ap-southeast-2 provided the contract includes the data residency addendum"
)

SECURITY = (
    "Security Baseline v2.3\n\n"
    "All laptops must use full-disk encryption. Screens lock after 5 minutes. "
    "Report lost devices to security@acme.example within 1 hour.\n\n\n"
    "Contractors\n"
    "Contractors follow the same baseline. Report lost devices to security@acme.example within 1 hour.\n"
    "Exceptions need written approval from the CISO!\n\n"
    "Questions? Ask in #sec-help."
)

TICKET = (
    "Ticket #48213 (priority: high)\n"
    "Customer: Northwind Traders\n"
    "Subject: SSO login loop after IdP certificate rotation\n\n"
    "Customer reports that users are redirected back to the Okta login page after entering credentials. "
    "It began at 09:14 UTC, right after they rotated the SAML signing certificate. "
    "Our logs show `InvalidSignature` for every assertion.\n\n"
    "Agent note: asked the customer to upload the new certificate under Settings > SSO > Certificates. "
    "Waiting on customer."
)

WIKI = "\n\n".join(
    "Section %d. The %s service owns %s. Deploys go out on %s. Escalate to %s." % (i, svc, what, day, team)
    for i, (svc, what, day, team) in enumerate([
        ("billing", "invoices and refunds", "Tuesdays", "#billing-oncall"),
        ("search", "the product catalog index", "Wednesdays", "#search-oncall"),
        ("identity", "SSO and SCIM provisioning", "Thursdays", "#identity-oncall"),
        ("notifications", "email and SMS delivery", "Mondays", "#notify-oncall"),
    ], 1)
)


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"document": PTO, "max_tokens": 24, "overlap_tokens": 0},
         "explanation": "45 tokens is too many, so cut at the two blank lines into pieces of 2, 25 and 18 tokens. The 25-token paragraph is still too big, "
                        "so it is cut at its sentence end into 16 + 9 (the '.' in '1.5' has no gap, so it is not a sentence end). Merging: 2 + 16 = 18 fits, "
                        "adding 9 would make 27 > 24, so close. 9 + 18 = 27 is too big again, so the last two pieces are separate chunks."},
        {"name": "Example 2", "hidden": False, "args": {"document": RUNBOOK, "max_tokens": 30, "overlap_tokens": 12},
         "explanation": "No blank lines, so cut at each newline into lines of 7, 12, 21 and 17 tokens. Lines 1 and 2 merge into 19. "
                        "Line 3 does not fit, and seeding with line 2 (12 tokens, within the 12-token overlap) would make 12 + 21 = 33 > 30, so the overlap is empty. "
                        "Line 3 (21 tokens) is over the overlap budget, so line 4 starts fresh too."},
        {"name": "Example 3", "hidden": False, "args": {"document": LONG_SENTENCE, "max_tokens": 12, "overlap_tokens": 3},
         "explanation": "One 42-token sentence with no separator, so it falls through to single-token pieces. Each new chunk is seeded with the previous chunk's last 3 tokens and takes 9 new ones; 'us-east-1' is 5 tokens and may be cut."},
        {"name": "empty and whitespace", "args": {"document": "  \n\n \t ", "max_tokens": 10, "overlap_tokens": 2}},
        {"name": "fits in one chunk", "args": {"document": PTO, "max_tokens": 45, "overlap_tokens": 5}},
        {"name": "one token over", "args": {"document": PTO, "max_tokens": 44, "overlap_tokens": 5}},
        {"name": "repeated sentence offsets", "args": {"document": SECURITY, "max_tokens": 16, "overlap_tokens": 0}},
        {"name": "repeated sentence with overlap", "args": {"document": SECURITY, "max_tokens": 20, "overlap_tokens": 8}},
        {"name": "ticket thread", "args": {"document": TICKET, "max_tokens": 40, "overlap_tokens": 10}},
        {"name": "ticket tight", "args": {"document": TICKET, "max_tokens": 9, "overlap_tokens": 4}},
        {"name": "wiki paragraphs", "args": {"document": WIKI, "max_tokens": 45, "overlap_tokens": 15}},
        {"name": "wiki sentence overlap", "args": {"document": WIKI, "max_tokens": 25, "overlap_tokens": 12}},
        {"name": "max_tokens 1", "args": {"document": "Reset MFA: Settings > Security.", "max_tokens": 1, "overlap_tokens": 0}},
        {"name": "version numbers are not sentences", "args": {"document": "Upgrade the agent to v2.3.1 before Friday. Older agents (v1.9) stop reporting.", "max_tokens": 9, "overlap_tokens": 2}},
    ]
