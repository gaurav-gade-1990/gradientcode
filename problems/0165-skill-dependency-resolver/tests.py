import numpy as np

REG = {
    "llm-core": {"1.4.0": {}, "1.9.2": {}, "1.10.0": {}, "2.0.0": {}},
    "http-tools": {"2.1.0": {"llm-core": "^1.4.0"}, "2.3.1": {"llm-core": "^1.9.0"}, "3.0.0": {"llm-core": "^2.0.0"}},
    "auth-oauth": {"0.3.0": {"http-tools": "^2.0.0"}, "0.3.4": {"http-tools": "^2.1.0"}, "0.4.0": {"http-tools": "^3.0.0"}},
    "crm-connector": {"1.0.0": {"auth-oauth": "^0.3.0", "http-tools": "~2.1.0"}, "1.2.0": {"auth-oauth": "^0.4.0", "llm-core": ">=2.0.0"}},
    "pdf-reader": {"0.9.0": {}, "1.0.0": {"llm-core": "^1.0.0"}, "1.1.0": {"llm-core": "^2.0.0"}},
    "vector-search": {"3.2.0": {"llm-core": ">=1.9.0 <2.0.0"}},
    "slack-notify": {"0.0.3": {"http-tools": "^2.0.0"}, "0.0.4": {"http-tools": "^3.0.0"}, "0.1.0": {"webhooks": "^1.0.0"}},
}


def _market(seed, n_pkgs=12, p_dep=0.25):
    """A synthetic marketplace. Deps only point at later skills (acyclic) and their ranges are built from real versions."""
    rng = np.random.default_rng(seed)
    names = ["skill-%s" % c for c in "abcdefghijklmnop"[:n_pkgs]]
    reg = {}
    for i in range(n_pkgs - 1, -1, -1):
        versions = {}
        for major in range(int(rng.integers(0, 2)), 2):
            for minor in range(int(rng.integers(1, 4))):
                deps = {}
                for j in range(i + 1, n_pkgs):
                    if rng.random() < p_dep:
                        target = sorted(reg[names[j]])[int(rng.integers(0, len(reg[names[j]])))]
                        kind = int(rng.integers(0, 5))
                        deps[names[j]] = ["^", "~", ">=", "<=", ""][kind] + target if kind < 5 else "*"
                versions["%d.%d.%d" % (major, minor, int(rng.integers(0, 3)))] = deps
        reg[names[i]] = versions
    return {n: reg[n] for n in names}, names


def cases():
    mk1, n1 = _market(165)
    mk2, n2 = _market(1650)
    return [
        {"name": "Example 1", "hidden": False, "args": {"registry": REG, "requirements": {"crm-connector": "^1.0.0", "pdf-reader": "^1.0.0"}},
         "explanation": "Nothing conflicts, so every package gets its highest allowed version: crm-connector 1.2.0 pulls auth-oauth 0.4.0, http-tools 3.0.0 and llm-core 2.0.0. "
                        "llm-core has no deps, so it installs first."},
        {"name": "Example 2", "hidden": False, "args": {"registry": REG, "requirements": {"crm-connector": "^1.0.0", "pdf-reader": "^1.0.0", "vector-search": "^3.2.0"}},
         "explanation": "vector-search needs llm-core below 2.0.0, which rules out crm-connector 1.2.0. Backtracking settles on crm-connector 1.0.0, llm-core 1.10.0 (10 > 9 numerically) "
                        "and pdf-reader 1.0.0, because pdf-reader 1.1.0 needs llm-core ^2.0.0."},
        {"name": "Example 3", "hidden": False, "args": {"registry": REG, "requirements": {"crm-connector": "^1.2.0", "vector-search": "*"}},
         "explanation": "No solution. The first dead end is llm-core: crm-connector 1.2.0 and http-tools 3.0.0 need 2.x, but vector-search 3.2.0 needs <2.0.0."},
        {"name": "empty manifest", "args": {"registry": REG, "requirements": {}}},
        {"name": "caret on 0.x", "args": {"registry": REG, "requirements": {"auth-oauth": "^0.3.0"}}},
        {"name": "caret on 0.0.x", "args": {"registry": REG, "requirements": {"slack-notify": "^0.0.3"}}},
        {"name": "tilde pins the minor", "args": {"registry": REG, "requirements": {"http-tools": "~2.1.0"}}},
        {"name": "numeric version order", "args": {"registry": REG, "requirements": {"llm-core": "^1.0.0", "pdf-reader": "<1.1.0"}}},
        {"name": "comparators", "args": {"registry": REG, "requirements": {"llm-core": ">1.4.0 <1.10.0", "http-tools": "=2.1.0", "pdf-reader": "<=1.0.0 >0.9.0"}}},
        {"name": "unknown skill", "args": {"registry": REG, "requirements": {"http-tools": "^2.0.0", "jira-sync": "^1.0.0"}}},
        {"name": "dependency missing from marketplace", "args": {"registry": REG, "requirements": {"slack-notify": ">=0.1.0"}}},
        {"name": "conflict with an already chosen version", "args": {"registry": REG, "requirements": {"llm-core": "=1.9.2", "pdf-reader": ">=1.1.0"}}},
        {"name": "root range unsatisfiable", "args": {"registry": REG, "requirements": {"vector-search": "^4.0.0"}}},
        {"name": "marketplace A", "args": {"registry": mk1, "requirements": {n1[0]: "*", n1[1]: "*", n1[3]: ">=0.0.0"}}},
        {"name": "marketplace B", "args": {"registry": mk2, "requirements": {n2[0]: "^1.0.0", n2[2]: "*", n2[5]: ">=0.1.0"}}},
        {"name": "marketplace B tight", "args": {"registry": mk2, "requirements": {n2[0]: "*", n2[1]: "~0.0.0", n2[4]: "*"}}},
    ]
