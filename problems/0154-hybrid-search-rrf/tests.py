VPN_BM25 = [
    ["it-wiki/vpn-setup#3", "it-wiki/vpn-setup", 14.2],
    ["tickets/INC-20417#1", "tickets/INC-20417", 11.8],
    ["it-wiki/password-policy#1", "it-wiki/password-policy", 9.5],
    ["it-wiki/vpn-setup#1", "it-wiki/vpn-setup", 7.1],
]
VPN_VEC = [
    ["it-wiki/password-policy#1", "it-wiki/password-policy", 0.83],
    ["it-wiki/vpn-setup#3", "it-wiki/vpn-setup", 0.81],
    ["it-wiki/sso-faq#2", "it-wiki/sso-faq", 0.77],
    ["tickets/INC-19920#2", "tickets/INC-19920", 0.74],
]

ERR_BM25 = [
    ["tickets/INC-30551#1", "tickets/INC-30551", 22.4],
    ["runbooks/payments-api#4", "runbooks/payments-api", 18.0],
    ["tickets/INC-30102#2", "tickets/INC-30102", 6.3],
]
ERR_VEC = [
    ["runbooks/payments-api#2", "runbooks/payments-api", 0.71],
    ["runbooks/payments-api#4", "runbooks/payments-api", 0.69],
    ["postmortems/2026-08-pay#1", "postmortems/2026-08-pay", 0.66],
]

# Two shards both returned the expense-policy chunk; the vector list also repeats one.
DUP_BM25 = [
    ["hr/expense-policy#2", "hr/expense-policy", 12.0],
    ["hr/expense-policy#2", "hr/expense-policy", 12.0],
    ["hr/travel-policy#1", "hr/travel-policy", 10.4],
    ["hr/per-diem-table#1", "hr/per-diem-table", 8.8],
]
DUP_VEC = [
    ["hr/per-diem-table#1", "hr/per-diem-table", 0.88],
    ["hr/travel-policy#1", "hr/travel-policy", 0.86],
    ["hr/per-diem-table#1", "hr/per-diem-table", 0.88],
    ["hr/expense-policy#2", "hr/expense-policy", 0.80],
]

# Huge BM25 scores on keyword spam vs. modest similarities.
SCALE_BM25 = [
    ["wiki/glossary#9", "wiki/glossary", 48.0],
    ["wiki/onboarding#2", "wiki/onboarding", 47.5],
    ["wiki/laptop-refresh#1", "wiki/laptop-refresh", 3.0],
]
SCALE_VEC = [
    ["wiki/laptop-refresh#1", "wiki/laptop-refresh", 0.92],
    ["wiki/onboarding#2", "wiki/onboarding", 0.40],
    ["wiki/hardware-catalog#3", "wiki/hardware-catalog", 0.35],
]

DEEP_BM25 = [["kb/sla#%d" % i, "kb/sla", 20.0 - i] for i in range(1, 9)]
DEEP_VEC = [["kb/escalation#1", "kb/escalation", 0.9], ["kb/sla#7", "kb/sla", 0.88], ["kb/sla#8", "kb/sla", 0.87],
            ["kb/escalation#2", "kb/escalation", 0.80], ["kb/sla#1", "kb/sla", 0.79]]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"query": "how do I reset my VPN password", "bm25_hits": VPN_BM25, "vector_hits": VPN_VEC, "top_n": 3, "candidates": 4},
         "explanation": "vpn-setup#3 is rank 1 and 2: 1/61 + 1/62 = 0.03252. password-policy#1 is rank 3 and 1: 1/63 + 1/61 = 0.03227. "
                        "INC-20417#1 is only in BM25 at rank 2: 1/62 = 0.01613, which beats sso-faq#2 at vector rank 3 (1/63). Raw scores are ignored."},
        {"name": "Example 2", "hidden": False,
         "args": {"query": "payments-api ERR_LEDGER_LOCK 503", "bm25_hits": ERR_BM25, "vector_hits": ERR_VEC, "top_n": 4, "candidates": 3,
                  "weights": {"bm25": 2.0}},
         "explanation": "An error-code query, so BM25 gets weight 2 and vector keeps the default 1. payments-api#4: 2/62 + 1/62 = 0.04839. "
                        "INC-30551#1: 2/61 = 0.03279. INC-30102#2: 2/63 = 0.03175. payments-api#2: 1/61 = 0.01639."},
        {"name": "duplicate hits count once", "args": {"query": "per diem for client travel", "bm25_hits": DUP_BM25, "vector_hits": DUP_VEC, "top_n": 3, "candidates": 4}},
        {"name": "raw scores ignored", "args": {"query": "when do I get a new laptop", "bm25_hits": SCALE_BM25, "vector_hits": SCALE_VEC, "top_n": 4, "candidates": 3}},
        {"name": "candidates deeper than top_n", "args": {"query": "SLA for sev2 escalation", "bm25_hits": DEEP_BM25, "vector_hits": DEEP_VEC, "top_n": 3, "candidates": 8}},
        {"name": "tie broken by chunk_id", "args": {"query": "badge access", "bm25_hits": [["kb/zz-badge#1", "kb/zz-badge", 5.0]],
                                                     "vector_hits": [["kb/aa-badge#1", "kb/aa-badge", 0.6]], "top_n": 2, "candidates": 10}},
        {"name": "tie broken by best rank", "args": {"query": "parental leave", "k": 10, "weights": {"vector": 2.0}, "top_n": 13, "candidates": 12,
            "bm25_hits": [["hr/leave#1", "hr/leave", 9.0]] + [["hr/misc#%d" % i, "hr/misc", 1.0] for i in range(2, 13)],
            "vector_hits": [["hr/benefits#%d" % i, "hr/benefits", 0.5] for i in range(1, 12)] + [["hr/aa-leave-faq#1", "hr/aa-leave-faq", 0.3]]}},
        {"name": "vector index empty", "args": {"query": "VPN", "bm25_hits": VPN_BM25, "vector_hits": [], "top_n": 3, "candidates": 4}},
        {"name": "both empty", "args": {"query": "quarterly OKRs", "bm25_hits": [], "vector_hits": [], "top_n": 5, "candidates": 5}},
        {"name": "fewer results than top_n", "args": {"query": "payments-api", "bm25_hits": ERR_BM25, "vector_hits": ERR_VEC, "top_n": 10, "candidates": 10, "k": 1}},
    ]
