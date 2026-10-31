import re

MISSING = object()


def glob_match(pattern, s):
    regex = "".join(".*" if ch == "*" else re.escape(ch) for ch in pattern)
    return re.fullmatch(regex, s, flags=re.S) is not None


def literals(pattern):
    return sum(1 for ch in pattern if ch != "*")


def resolve(request, path):
    cur = request
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return MISSING
        cur = cur[part]
    return cur


def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def condition_holds(request, cond):
    left = resolve(request, cond["attr"])
    right = cond["value"]
    if isinstance(right, dict) and "attr" in right:
        right = resolve(request, right["attr"])
    if left is MISSING or right is MISSING:
        return False
    op = cond["op"]
    if op == "eq":
        return left == right
    if op == "neq":
        return left != right
    if op in ("in", "not_in"):
        if not isinstance(right, list):
            return False
        return (left in right) == (op == "in")
    if op in ("lt", "lte", "gt", "gte"):
        if not (is_number(left) and is_number(right)):
            return False
        return {"lt": left < right, "lte": left <= right, "gt": left > right, "gte": left >= right}[op]
    return False


def best_literal(patterns, s):
    hits = [literals(p) for p in patterns if glob_match(p, s)]
    return max(hits) if hits else None


def match(rule, request):
    """Return the specificity tuple if the rule matches, else None."""
    p = request["principal"]
    identities = [p["id"]] + ["role:" + r for r in p.get("roles") or []]
    if not any(glob_match(pat, ident) for pat in rule["principals"] for ident in identities):
        return None
    a = best_literal(rule["actions"], request["action"])
    r = best_literal(rule["resources"], request["resource"]["id"])
    if a is None or r is None:
        return None
    conds = rule.get("conditions") or []
    if not all(condition_holds(request, c) for c in conds):
        return None
    return (r, a, len(conds))


def decide(rules, request):
    hits = []
    for i, rule in enumerate(rules):
        spec = match(rule, request)
        if spec is not None:
            hits.append((spec, i, rule))
    matched = [rule["id"] for _, _, rule in hits]
    denies = [h for h in hits if h[2]["effect"] == "deny"]
    allows = [h for h in hits if h[2]["effect"] == "allow"]
    if not hits:
        return {"decision": "deny", "reason": "no_match", "rule": None, "matched": matched}
    best = min(hits, key=lambda h: (tuple(-x for x in h[0]), h[1]))
    decision, reason = ("deny", "explicit_deny") if best[2]["effect"] == "deny" else ("allow", "allowed")
    return {"decision": decision, "reason": reason, "rule": best[2]["id"], "matched": matched}


def evaluate(rules, requests):
    return [decide(rules, req) for req in requests]
