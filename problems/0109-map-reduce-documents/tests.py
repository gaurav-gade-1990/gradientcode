POLICY = {"id": "refund-policy", "text": "Refunds are accepted within 30 days of delivery. Items must be unused and in the original packaging. Final sale items cannot be refunded."}
SLA = {"id": "sla", "text": "Premium customers get a reply within 4 business hours. Standard customers get a reply within 2 business days."}
OUTAGE = {"id": "incident-311", "text": "On Oct 28 the payments API returned 503 errors for 42 minutes. Root cause: an expired TLS certificate on the card-vault proxy. Mitigation: rotate the certificate and add expiry alerts at 30 and 7 days."}
SHORT = {"id": "note", "text": "Escalate fraud to Tier 2."}
EMPTY = {"id": "blank", "text": ""}


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"docs": [POLICY, SLA], "chunk_tokens": 12, "max_concurrency": 2, "batch_size": 2},
         "explanation": "The two docs make 5 chunks of at most 12 tokens. Map runs 2 at a time, starting the next chunk as soon as a slot frees. Reduce pairs [s1,s2] and [s3,s4] and carries s5 through without a call; the next levels make 2 more calls until one summary is left."},
        {"name": "Example 2", "hidden": False, "args": {"docs": [SHORT], "chunk_tokens": 50, "max_concurrency": 3, "batch_size": 4},
         "explanation": "One chunk, one map call, and no reduce at all: its summary is the final answer."},
        {"name": "empty input", "args": {"docs": [EMPTY], "chunk_tokens": 10, "max_concurrency": 2, "batch_size": 3}},
        {"name": "partial last chunk kept", "args": {"docs": [OUTAGE], "chunk_tokens": 20, "max_concurrency": 2, "batch_size": 2}},
        {"name": "completion order differs from chunk order", "args": {"docs": [OUTAGE, SHORT, POLICY, EMPTY, SLA], "chunk_tokens": 15, "max_concurrency": 3, "batch_size": 3}},
        {"name": "serial", "args": {"docs": [POLICY, SLA], "chunk_tokens": 12, "max_concurrency": 1, "batch_size": 2}},
        {"name": "wide concurrency", "args": {"docs": [POLICY, SLA, OUTAGE], "chunk_tokens": 8, "max_concurrency": 6, "batch_size": 4}},
        {"name": "batch of everything", "args": {"docs": [POLICY, OUTAGE], "chunk_tokens": 10, "max_concurrency": 4, "batch_size": 10}},
        {"name": "tiny chunks deep tree", "args": {"docs": [SLA, SHORT], "chunk_tokens": 3, "max_concurrency": 4, "batch_size": 2}},
        {"name": "exact multiple of chunk size", "args": {"docs": [{"id": "x", "text": "one two three four five six seven eight"}], "chunk_tokens": 4, "max_concurrency": 2, "batch_size": 2}},
    ]
