import numpy as np

TEAM = [
    {"name": "billing-bot", "skills": ["billing", "refunds"], "capacity": 2, "speed": 1.0},
    {"name": "refunds-pro", "skills": ["refunds"], "capacity": 1, "speed": 2.0},
    {"name": "contracts-ai", "skills": ["contracts", "billing"], "capacity": 1, "speed": 0.5},
]


def Q(id, arrives, skill, minutes, deadline):
    return {"id": id, "arrives": arrives, "skill": skill, "minutes": minutes, "deadline": deadline}


def _load(n, seed):
    rng = np.random.default_rng(seed)
    out = []
    for k in range(n):
        arrives = int(rng.integers(0, 240))
        minutes = int(rng.integers(5, 60))
        slack = int(rng.integers(0, 90))
        out.append(Q("REQ-%03d" % k, arrives, ["billing", "refunds", "contracts", "legal"][int(rng.choice(4, p=[0.4, 0.35, 0.2, 0.05]))], minutes, arrives + minutes // 2 + slack))
    return out


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"coworkers": TEAM, "requests": [
            Q("T-1", 0, "refunds", 30, 60), Q("T-2", 0, "refunds", 30, 40), Q("T-3", 0, "legal", 10, 100)]},
         "explanation": "At t=0 the queue is walked in deadline order: T-2 (40), T-1 (60), T-3 (100). T-2 goes to refunds-pro (speed 2, finishes at 15). "
                        "T-1 goes to billing-bot (finishes at 30). Nobody has the legal skill, so T-3 is escalated."},
        {"name": "Example 2", "hidden": False, "args": {"coworkers": TEAM, "requests": [
            Q("T-10", 0, "contracts", 20, 40), Q("T-11", 5, "contracts", 20, 90), Q("T-12", 5, "contracts", 20, 50)]},
         "explanation": "contracts-ai is the only contracts coworker and takes 40 minutes per request. T-10 finishes at 40. At t=5 T-12 (deadline 50) could make it "
                        "if it started now, but contracts-ai is busy, so it waits. At t=40 it would finish at 80 > 50, so it is escalated, and T-11 is assigned instead."},
        {"name": "Example 3", "hidden": False, "args": {"coworkers": TEAM, "requests": [Q("T-20", 0, "billing", 10, 10), Q("T-21", 0, "billing", 10, 9)]},
         "explanation": "T-21 needs 10 minutes on the fastest billing coworker but has 9, so it is escalated at once. T-20 finishes exactly at its deadline, which meets the SLA."},
        {"name": "empty inbox", "args": {"coworkers": TEAM, "requests": []}},
        {"name": "edf beats fifo", "args": {"coworkers": [{"name": "solo", "skills": ["billing"], "capacity": 1, "speed": 1.0}], "requests": [
            Q("A", 0, "billing", 10, 100), Q("B", 0, "billing", 10, 30), Q("C", 1, "billing", 10, 21), Q("D", 2, "billing", 10, 45)]}},
        {"name": "wait for the fast one", "args": {"coworkers": [{"name": "slow", "skills": ["refunds"], "capacity": 3, "speed": 0.25},
                                                               {"name": "fast", "skills": ["refunds"], "capacity": 1, "speed": 4.0}],
                                                 "requests": [Q("R1", 0, "refunds", 40, 20), Q("R2", 1, "refunds", 20, 20), Q("R3", 2, "refunds", 4, 200)]}},
        {"name": "choose earliest finish then load then name", "args": {"coworkers": [
            {"name": "zeta", "skills": ["billing"], "capacity": 3, "speed": 2.0}, {"name": "alpha", "skills": ["billing"], "capacity": 3, "speed": 2.0},
            {"name": "beta", "skills": ["billing"], "capacity": 3, "speed": 1.0}],
            "requests": [Q("B%d" % k, 0, "billing", 8, 100) for k in range(7)]}},
        {"name": "same time completion and arrival", "args": {"coworkers": [{"name": "solo", "skills": ["billing"], "capacity": 1, "speed": 1.0}],
                                                              "requests": [Q("X", 0, "billing", 10, 10), Q("Y", 10, "billing", 5, 15), Q("Z", 3, "billing", 5, 15)]}},
        {"name": "unsorted input", "args": {"coworkers": TEAM, "requests": [Q("T-9", 50, "billing", 30, 200), Q("T-1", 0, "refunds", 60, 70),
                                                                            Q("T-5", 20, "refunds", 60, 120), Q("T-3", 0, "contracts", 10, 25)]}},
        {"name": "busy afternoon", "args": {"coworkers": TEAM, "requests": _load(120, 164)}},
        {"name": "bigger team", "args": {"coworkers": TEAM + [{"name": "legal-ai", "skills": ["legal", "contracts"], "capacity": 2, "speed": 1.0},
                                                             {"name": "generalist", "skills": ["billing", "refunds", "contracts"], "capacity": 4, "speed": 0.5}],
                                        "requests": _load(250, 1640)}},
    ]
