def grants(grant_list, scope):
    for g in grant_list:
        if g == scope or g == "*":
            return True
        if g.endswith(":*") and scope.startswith(g[:-1]):
            return True
    return False


def authorize_calls(user, agent, role_scopes, tools, resources, calls):
    user_grants = [g for r in user["roles"] for g in role_scopes.get(r, [])]
    agent_grants = agent["scopes"]

    common = set(user_grants) & set(agent_grants)

    def effective(scope):
        return grants(list(common), scope)

    def decide(call):
        tool = tools.get(call["tool"])
        if tool is None:
            return "unknown_tool", []
        if call["tool"] not in agent["allowed_tools"]:
            return "agent_tool_not_allowed", []
        missing = sorted(s for s in tool["scopes"] if not effective(s))
        if missing:
            return "missing_scopes", missing
        arg = tool.get("resource_arg")
        if arg is None:
            return None, []
        rid = call["arguments"].get(arg)
        if not isinstance(rid, str) or rid not in resources:
            return "resource_not_found", []
        res = resources[rid]
        if res["tenant"] != user["tenant"]:
            return "cross_tenant", []
        admin = tool.get("admin_scope")
        if res["owner"] != user["id"] and not (admin and effective(admin)):
            return "not_owner", []
        return None, []

    out = []
    for call in calls:
        reason, missing = decide(call)
        out.append({"id": call["id"], "allowed": reason is None, "reason": reason, "missing": missing})
    return out
