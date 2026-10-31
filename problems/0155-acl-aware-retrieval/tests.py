CHUNKS = [
    {"chunk_id": "hr/salary-bands-2026#1", "doc_id": "hr/salary-bands-2026", "text": "Salary bands for 2026: Senior Engineer L5 base pay ranges from 182k to 236k."},
    {"chunk_id": "hr/salary-bands-2026#2", "doc_id": "hr/salary-bands-2026", "text": "Staff Engineer L6 base pay ranges from 221k to 289k. Bands are reviewed every March."},
    {"chunk_id": "hr/pto-policy#1", "doc_id": "hr/pto-policy", "text": "Employees accrue 1.5 days of PTO per month. Senior staff may carry over 10 days."},
    {"chunk_id": "eng/oncall-handbook#1", "doc_id": "eng/oncall-handbook", "text": "On-call engineers acknowledge pages within 5 minutes. Senior Engineer escalation goes to the SRE lead."},
    {"chunk_id": "eng/incident-db-outage#1", "doc_id": "eng/incident-db-outage", "text": "Incident 2026-10-02: the primary Postgres ran out of disk. Senior Engineer on call failed over in 14 minutes."},
    {"chunk_id": "legal/project-falcon#1", "doc_id": "legal/project-falcon", "text": "Project Falcon: acquisition term sheet. Retention pay for each Senior Engineer is 50k over 2 years."},
    {"chunk_id": "wiki/holiday-calendar#1", "doc_id": "wiki/holiday-calendar", "text": "Company holidays for 2026 include November 26 and 27 and December 24 to January 1."},
    {"chunk_id": "wiki/imported-confluence#1", "doc_id": "wiki/imported-confluence", "text": "Old salary spreadsheet export: Senior Engineer base pay by person and level."},
]

GROUPS = {
    "all-employees": {"members": ["ceo"], "subgroups": ["engineering", "sales", "people-ops"]},
    "engineering": {"members": [], "subgroups": ["sre", "platform"]},
    "sre": {"members": ["maya.chen"], "subgroups": []},
    "platform": {"members": ["lee.kim", "omar.haddad"], "subgroups": []},
    "sales": {"members": ["raj.patel"], "subgroups": []},
    "people-ops": {"members": [], "subgroups": ["hr-comp"]},
    "hr-comp": {"members": ["dana.ortiz"], "subgroups": []},
    "contractors": {"members": ["lee.kim"], "subgroups": []},
    "managers": {"members": ["maya.chen", "dana.ortiz"], "subgroups": []},
}

ACLS = {
    "hr/salary-bands-2026": {"allow_groups": ["hr-comp", "managers"], "deny_groups": ["contractors"]},
    "hr/pto-policy": {"allow_groups": ["all-employees"]},
    "eng/oncall-handbook": {"allow_groups": ["engineering"], "deny_users": ["omar.haddad"]},
    "eng/incident-db-outage": {"allow_groups": ["sre", "engineering"]},
    "legal/project-falcon": {"allow_users": ["ceo", "general.counsel"], "deny_groups": ["all-employees"]},
    "wiki/holiday-calendar": {"allow_groups": ["all-employees", "contractors"]},
}

QUERY = "Senior Engineer salary base pay"

# Cyclic IdP sync: two groups list each other.
CYCLE_GROUPS = dict(GROUPS)
CYCLE_GROUPS["platform"] = {"members": ["lee.kim", "omar.haddad"], "subgroups": ["infra-guild"]}
CYCLE_GROUPS["infra-guild"] = {"members": ["priya.nair"], "subgroups": ["platform", "ghost-group"]}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"user_id": "maya.chen", "query": QUERY, "k": 3, "chunks": CHUNKS, "acls": ACLS, "groups": GROUPS},
         "explanation": "maya.chen is in sre and managers, and sre sits in engineering, which sits in all-employees. She sees the salary bands through managers "
                        "and the on-call handbook through engineering. Project Falcon denies all-employees, and the imported Confluence page has no ACL, "
                        "so the index is searched over 5 allowed docs only."},
        {"name": "Example 2", "hidden": False,
         "args": {"user_id": "lee.kim", "query": QUERY, "k": 3, "chunks": CHUNKS, "acls": ACLS, "groups": GROUPS},
         "explanation": "lee.kim is on platform (inside engineering) and is also in contractors. The salary bands deny contractors and the incident doc allows "
                        "sre or engineering, so she gets the incident doc but not the bands. Because the filter is applied inside the search, all 3 slots are "
                        "filled from her docs. Searching first would have spent them on salary chunks."},
        {"name": "Example 3", "hidden": False,
         "args": {"user_id": "visitor.badge", "query": QUERY, "k": 3, "chunks": CHUNKS, "acls": ACLS, "groups": GROUPS},
         "explanation": "A user in no group can open nothing, so the index is never called."},
        {"name": "hr comp two levels deep", "args": {"user_id": "dana.ortiz", "query": QUERY, "k": 4, "chunks": CHUNKS, "acls": ACLS, "groups": GROUPS}},
        {"name": "direct deny beats group allow", "args": {"user_id": "omar.haddad", "query": "on-call escalation pages", "k": 3, "chunks": CHUNKS, "acls": ACLS, "groups": GROUPS}},
        {"name": "group deny beats direct allow", "args": {"user_id": "ceo", "query": "Project Falcon retention pay", "k": 2, "chunks": CHUNKS, "acls": ACLS, "groups": GROUPS}},
        {"name": "allow user outside every group", "args": {"user_id": "general.counsel", "query": "Project Falcon retention pay", "k": 5, "chunks": CHUNKS, "acls": ACLS, "groups": GROUPS}},
        {"name": "sales sees only company docs", "args": {"user_id": "raj.patel", "query": QUERY, "k": 5, "chunks": CHUNKS, "acls": ACLS, "groups": GROUPS}},
        {"name": "cyclic groups", "args": {"user_id": "priya.nair", "query": "Postgres incident failover", "k": 3, "chunks": CHUNKS, "acls": ACLS, "groups": CYCLE_GROUPS}},
        {"name": "k larger than allowed chunks", "args": {"user_id": "maya.chen", "query": "holidays in December", "k": 20, "chunks": CHUNKS, "acls": ACLS, "groups": GROUPS}},
        {"name": "smallest matching group named", "args": {"user_id": "maya.chen", "query": "disk", "k": 1, "chunks": CHUNKS, "groups": GROUPS,
            "acls": {"eng/incident-db-outage": {"allow_groups": ["sre", "managers", "engineering"]}, "hr/pto-policy": {"deny_groups": ["sre", "managers"], "allow_users": ["maya.chen"]}}}},
    ]
