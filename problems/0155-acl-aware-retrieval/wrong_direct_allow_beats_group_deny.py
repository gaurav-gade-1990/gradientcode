def user_groups(user_id, groups):
    """Every group the user belongs to, directly or through any chain of subgroups."""
    parents = {}
    for g, spec in groups.items():
        for sub in spec.get("subgroups", []):
            parents.setdefault(sub, []).append(g)
    found = set()
    stack = [g for g, spec in groups.items() if user_id in spec.get("members", [])]
    while stack:
        g = stack.pop()
        if g in found:
            continue
        found.add(g)
        stack.extend(parents.get(g, []))
    return found


def decide(user_id, mine, acl):
    if acl is None:
        return "deny:no_acl"
    if user_id in acl.get("deny_users", []):
        return "deny:user"
    # A direct grant short-circuits group denies, so an offboarded group never loses access.
    if user_id in acl.get("allow_users", []):
        return "allow:user"
    hit = sorted(set(acl.get("deny_groups", [])) & mine)
    if hit:
        return "deny:group:" + hit[0]
    hit = sorted(set(acl.get("allow_groups", [])) & mine)
    if hit:
        return "allow:group:" + hit[0]
    return "deny:default"


def search_with_acl(user_id, query, k, index, acls, groups):
    mine = user_groups(user_id, groups)
    decisions = {d: decide(user_id, mine, acls.get(d)) for d in index.doc_ids()}
    allowed = sorted(d for d, r in decisions.items() if r.startswith("allow"))
    results = index.search(query, k, allowed) if allowed else []
    return {"decisions": decisions, "results": results}
