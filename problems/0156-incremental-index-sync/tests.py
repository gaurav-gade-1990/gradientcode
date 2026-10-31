import hashlib


def _h(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def manifest_of(docs):
    """Yesterday's manifest: what a correct sync left behind for these doc versions."""
    out = {}
    for doc_id, text in docs.items():
        ids, seen = [], {}
        for p in [p.strip() for p in text.split("\n\n") if p.strip()]:
            ids.append("%s:%s:%d" % (doc_id, _h(p)[:12], seen.get(p, 0)))
            seen[p] = seen.get(p, 0) + 1
        out[doc_id] = {"content_hash": _h(text), "chunk_ids": ids}
    return out


PTO_V1 = ("PTO Policy\n\n"
          "Full-time employees accrue 1.5 days of PTO per month.\n\n"
          "Unused PTO carries over up to 10 days.")
PTO_V2 = ("PTO Policy\n\n"
          "Full-time employees accrue 1.75 days of PTO per month, effective January 1.\n\n"
          "Unused PTO carries over up to 10 days.")
VPN = ("VPN Setup\n\n"
       "Install the GlobalProtect client from the Self Service portal.\n\n"
       "Use your SSO credentials and approve the Okta push.")
PAYMENTS = ("Runbook: payments-api\n\n"
            "Check the error budget dashboard first.\n\n"
            "Roll back with deployctl if the spike follows a deploy.")
LEAVE = ("Parental Leave\n\n"
         "Birthing parents get 16 weeks of paid leave. Non-birthing parents get 12 weeks.")
SECURITY_V1 = ("Security Baseline\n\n"
               "Report lost devices within 1 hour.\n\n"
               "Contractors\n\n"
               "Report lost devices within 1 hour.")
SECURITY_V2 = ("Security Baseline v2\n\n"
               "Report lost devices within 1 hour.\n\n"
               "Contractors\n\n"
               "Report lost devices within 1 hour.\n\n"
               "Report lost devices within 1 hour.")
ONCALL_V1 = "On-call Handbook\n\nAcknowledge pages within 5 minutes.\n\nEscalate sev1 to the incident commander."
ONCALL_V2 = "On-call Handbook\n\nAcknowledge pages within 5 minutes.\n\nEscalate sev1 to the incident commander.\n\nHand off at 09:00 local time."
ONCALL_V3 = "On-call Handbook\n\n\n\nAcknowledge pages within 5 minutes.   \n\nEscalate sev1 to the incident commander."
ONCALL_TOP = "Read this first: the pager rotation changed on November 1.\n\n" + ONCALL_V1

YESTERDAY = {"hr/pto-policy": PTO_V1, "it/vpn-setup": VPN, "runbooks/payments-api": PAYMENTS}


def src(docs):
    return [{"doc_id": d, "text": t} for d, t in docs.items()]


def cases():
    big_yesterday = {"wiki/page-%02d" % i: "Page %d\n\nOwner: team %d." % (i, i % 3) for i in range(1, 11)}
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"source_docs": src({"it/vpn-setup": VPN, "hr/pto-policy": PTO_V2, "runbooks/payments-api": PAYMENTS, "hr/parental-leave": LEAVE}),
                  "manifest": manifest_of(YESTERDAY)},
         "explanation": "The VPN and payments docs hash the same, so they cost nothing. parental-leave is new: one embed call for its 2 chunks, then one upsert. "
                        "pto-policy changed in one paragraph only: its other two chunk ids are content-derived and still match, so only the new paragraph is "
                        "embedded and upserted, and then the old one is deleted."},
        {"name": "Example 2", "hidden": False,
         "args": {"source_docs": src({"it/vpn-setup": VPN, "hr/pto-policy": PTO_V1}), "manifest": manifest_of(YESTERDAY)},
         "explanation": "The payments runbook is gone from the source. 1 of 3 docs deleted is within the 0.5 guard, so its 3 chunks are deleted (a tombstone) "
                        "and it leaves the manifest."},
        {"name": "Example 3", "hidden": False,
         "args": {"source_docs": [], "manifest": manifest_of(YESTERDAY)},
         "explanation": "The connector returned nothing, which almost always means an auth or API failure, not that the company deleted its wiki. "
                        "Abort with no calls."},
        {"name": "first sync from empty", "args": {"source_docs": src(YESTERDAY), "manifest": {}}},
        {"name": "empty source and empty manifest", "args": {"source_docs": [], "manifest": {}}},
        {"name": "paragraph inserted at top", "args": {"source_docs": src({"eng/oncall": ONCALL_TOP}), "manifest": manifest_of({"eng/oncall": ONCALL_V1})}},
        {"name": "paragraph appended", "args": {"source_docs": src({"eng/oncall": ONCALL_V2}), "manifest": manifest_of({"eng/oncall": ONCALL_V1})}},
        {"name": "whitespace-only edit", "args": {"source_docs": src({"eng/oncall": ONCALL_V3}), "manifest": manifest_of({"eng/oncall": ONCALL_V1})}},
        {"name": "repeated paragraphs", "args": {"source_docs": src({"sec/baseline": SECURITY_V2}), "manifest": manifest_of({"sec/baseline": SECURITY_V1})}},
        {"name": "repeated paragraphs first sync", "args": {"source_docs": src({"sec/baseline": SECURITY_V1, "hr/pto-policy": PTO_V1}), "manifest": {}}},
        {"name": "guard trips over fraction", "args": {"source_docs": src({"wiki/page-%02d" % i: big_yesterday["wiki/page-%02d" % i] for i in range(1, 5)}),
                                                        "manifest": manifest_of(big_yesterday), "max_delete_fraction": 0.5}},
        {"name": "guard boundary is inclusive", "args": {"source_docs": src({"wiki/page-%02d" % i: big_yesterday["wiki/page-%02d" % i] for i in range(1, 6)}),
                                                          "manifest": manifest_of(big_yesterday), "max_delete_fraction": 0.5}},
        {"name": "mixed night", "args": {"source_docs": src({"hr/pto-policy": PTO_V2, "eng/oncall": ONCALL_TOP, "sec/baseline": SECURITY_V2, "hr/parental-leave": LEAVE}),
                                          "manifest": manifest_of({"hr/pto-policy": PTO_V1, "eng/oncall": ONCALL_V1, "sec/baseline": SECURITY_V1, "it/vpn-setup": VPN}),
                                          "max_delete_fraction": 0.25}},
        {"name": "doc emptied out", "args": {"source_docs": src({"it/vpn-setup": "   \n\n  ", "hr/pto-policy": PTO_V1}), "manifest": manifest_of({"it/vpn-setup": VPN, "hr/pto-policy": PTO_V1})}},
    ]
