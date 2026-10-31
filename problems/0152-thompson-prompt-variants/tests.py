import numpy as np


def _requests(rng, n, rates, prefix="conv"):
    return [{"request_id": "%s-%03d" % (prefix, i), "outcomes": {vid: int(rng.random() < p) for vid, p in rates.items()}} for i in range(n)]


def V(vid, launch, parent=None):
    return {"id": vid, "launch_at": launch, "warm_start_from": parent}


def _uniforms(rng, n):
    return [round(float(x), 6) for x in rng.random(n)]


def cases():
    rng = np.random.default_rng(152)
    ex1_req = [
        {"request_id": "conv-001", "outcomes": {"concise": 1, "friendly": 0}},
        {"request_id": "conv-002", "outcomes": {"concise": 0, "friendly": 1}},
        {"request_id": "conv-003", "outcomes": {"concise": 1, "friendly": 1}},
    ]
    ex2_req = [
        {"request_id": "conv-101", "outcomes": {"v1": 1, "v1-short": 1}},
        {"request_id": "conv-102", "outcomes": {"v1": 1, "v1-short": 0}},
        {"request_id": "conv-103", "outcomes": {"v1": 0, "v1-short": 1}},
    ]
    three = [V("baseline", 0), V("checklist", 0), V("socratic", 0)]
    big3 = _requests(rng, 100, {"baseline": 0.35, "checklist": 0.55, "socratic": 0.30})
    launch = [V("v1", 0), V("v1-tone", 40, "v1"), V("v2-cold", 60)]
    big_launch = _requests(rng, 110, {"v1": 0.5, "v1-tone": 0.62, "v2-cold": 0.45})
    chain = [V("a", 0), V("b", 10, "a"), V("c", 20, "b"), V("d", 30, "c")]
    big_chain = _requests(rng, 50, {"a": 0.8, "b": 0.2, "c": 0.6, "d": 0.7})
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"variants": [V("concise", 0), V("friendly", 0)], "requests": ex1_req, "warm_weight": 0, "uniforms": [0.9, 0.2, 0.3, 0.7, 0.5, 0.5]},
         "explanation": "Request 1: Beta(1, 1) draws are just the uniforms, 0.9 vs 0.2, so concise is served and succeeds, giving (2, 1). Request 2: concise's Beta(2, 1) quantile at 0.3 is sqrt(0.3) = 0.548 vs friendly's 0.7, so friendly is served and succeeds. Request 3: sqrt(0.5) = 0.707 vs 0.707 for Beta(2, 1) at 0.5, an exact tie, so the earlier variant (concise) is served."},
        {"name": "Example 2", "hidden": False,
         "args": {"variants": [V("v1", 0), V("v1-short", 2, "v1")], "requests": ex2_req, "warm_weight": 10, "uniforms": [0.4, 0.4, 0.6, 0.1]},
         "explanation": "v1 serves alone for two requests and wins both: (3, 1). v1-short launches at request index 2: s = (10 * 3) // 4 = 7, so its prior is (8, 4). The draws are Beta(3, 1) at 0.6 and Beta(8, 4) at 0.1, which serves v1, and v1 fails. v1-short's mean 8/12 beats v1's 3/5, but it never served, so v1 is the leader."},
        {"name": "Example 3", "hidden": False,
         "args": {"variants": [V("only", 0)], "requests": [{"request_id": "conv-201", "outcomes": {"only": 1}}, {"request_id": "conv-202", "outcomes": {"only": 0}}], "warm_weight": 5, "uniforms": [0.5, 0.5]},
         "explanation": "One active variant still gets one draw per request, and its posterior (2, 2) has mean 1/2."},
        {"name": "three arms from cold", "args": {"variants": three, "requests": big3, "warm_weight": 0, "uniforms": _uniforms(rng, 300)}},
        {"name": "warm launch and cold launch", "args": {"variants": launch, "requests": big_launch, "warm_weight": 20, "uniforms": _uniforms(rng, 300)}},
        {"name": "warm-start chain", "args": {"variants": chain, "requests": big_chain, "warm_weight": 8, "uniforms": _uniforms(rng, 200)}},
        {"name": "leader tie by list order", "args": {"variants": [V("x", 0), V("y", 0)], "requests": [{"request_id": "r1", "outcomes": {"x": 1, "y": 1}}, {"request_id": "r2", "outcomes": {"x": 1, "y": 1}}],
                                                      "warm_weight": 0, "uniforms": [0.2, 0.8, 0.95, 0.1]}},
        {"name": "zero warm weight", "args": {"variants": [V("base", 0), V("fork", 5, "base")], "requests": _requests(rng, 30, {"base": 0.9, "fork": 0.1}),
                                              "warm_weight": 0, "uniforms": _uniforms(rng, 60)}},
    ]
