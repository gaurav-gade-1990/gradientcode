def C(cid, pos, score, text):
    return {"chunk_id": cid, "doc_id": cid.split("#")[0], "position": pos, "score": score, "text": text}


EXPENSE = [
    C("hr/expense-policy#2", 2, 0.91, "Submit receipts in Expensify within 30 days of the purchase."),
    C("hr/expense-policy#0", 0, 0.84, "Employees are reimbursed for reasonable business expenses."),
    C("wiki-export/expense-policy-old#4", 4, 0.88, "Submit receipts in Expensify within 30 days of purchase."),
    C("finance/travel-faq#1", 1, 0.62, "Hotel stays above $250 per night need VP approval before booking."),
    C("hr/expense-policy#5", 5, 0.70, "Meals with clients are capped at $75 per person including tip, and alcohol is reimbursed only "
                                      "when a client is present and the receipt lists every attendee by name and company."),
]

ONCALL = [
    C("eng/oncall#1", 1, 0.95, "Acknowledge the page within 5 minutes."),
    C("eng/oncall#3", 3, 0.93, "If the database is the cause, page the DBA on-call."),
    C("eng/oncall#2", 2, 0.90, "Open an incident channel named #inc-<date>-<service>."),
    C("eng/oncall#4", 4, 0.89, "Post a status update every 30 minutes until resolved."),
    C("eng/sev-matrix#0", 0, 0.80, "Sev1 means customers cannot pay or log in."),
    C("eng/postmortem-guide#0", 0, 0.60, "Write the postmortem within 5 business days."),
]

LEAVE = [
    C("hr/leave#0", 0, 0.90, "Parental leave is 16 weeks for birthing parents and 12 weeks for non-birthing parents."),
    C("hr/leave-2024#0", 0, 0.89, "PARENTAL LEAVE is 16 weeks for birthing parents and 12 weeks for non-birthing parents!"),
    C("hr/leave#1", 1, 0.85, "Leave can start up to 4 weeks before the expected due date."),
    C("hr/leave-faq#3", 3, 0.85, "Leave can start up to 4 weeks before the due date and must be taken within 12 months."),
    C("benefits/overview#7", 7, 0.40, "Benefits enrollment opens every November."),
]


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"chunks": EXPENSE, "budget": 90, "max_per_doc": 3, "dedupe_threshold": 0.8},
         "explanation": "The old wiki export repeats the receipts rule (Jaccard 10/11 >= 0.8), so it is dropped as a duplicate of hr/expense-policy#2. "
                        "By score per token, #0 (26 tokens with its wrapper), #2 (29) and the travel FAQ (31) fit in 86 tokens. The 52-token meals chunk does not "
                        "fit in the 4 that are left. The expense policy comes first (best score 0.91), and inside it #0 comes before #2 by position."},
        {"name": "Example 2", "hidden": False, "args": {"chunks": ONCALL, "budget": 200, "max_per_doc": 2, "dedupe_threshold": 0.9},
         "explanation": "The on-call doc has four strong chunks but max_per_doc = 2. The two best by score per token are picked, and the other two are dropped with "
                        "doc_cap, which leaves room for the severity matrix and the postmortem guide."},
        {"name": "case-insensitive dedupe", "args": {"chunks": LEAVE, "budget": 300, "max_per_doc": 3, "dedupe_threshold": 0.85}},
        {"name": "dedupe threshold boundary", "args": {"chunks": LEAVE, "budget": 300, "max_per_doc": 3, "dedupe_threshold": 0.6}},
        {"name": "no dedupe at 1.0", "args": {"chunks": EXPENSE, "budget": 500, "max_per_doc": 5, "dedupe_threshold": 1.0}},
        {"name": "smaller chunk fills the gap", "args": {"chunks": EXPENSE + [C("finance/mileage#0", 0, 0.30, "Mileage is 67 cents per mile.")], "budget": 110, "max_per_doc": 3, "dedupe_threshold": 0.8}},
        {"name": "budget below every chunk", "args": {"chunks": ONCALL, "budget": 12, "max_per_doc": 2, "dedupe_threshold": 0.9}},
        {"name": "density beats raw score", "args": {"chunks": EXPENSE + [C("finance/per-diem#0", 0, 0.66, "Per diem: $60.")], "budget": 110, "max_per_doc": 3, "dedupe_threshold": 0.8}},
        {"name": "one per doc", "args": {"chunks": ONCALL + LEAVE, "budget": 400, "max_per_doc": 1, "dedupe_threshold": 0.85}},
        {"name": "everything fits, reading order", "args": {"chunks": ONCALL, "budget": 1000, "max_per_doc": 10, "dedupe_threshold": 0.9}},
        {"name": "single chunk", "args": {"chunks": [EXPENSE[0]], "budget": 100, "max_per_doc": 1, "dedupe_threshold": 0.5}},
    ]
