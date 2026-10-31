from gc_runtime import stable_hash


def _rule_matches(rule, attrs):
    if rule["attr"] not in attrs:
        return False
    v = attrs[rule["attr"]]
    if rule["op"] == "eq":
        return v == rule["value"]
    if rule["op"] == "in":
        return v in rule["value"]
    return False


def _evaluate(flag, user):
    key = flag["key"]
    bucket = stable_hash("%s:%s:%s" % (key, user["tenant"], user["id"]), 10000)
    tenants = flag.get("tenants") or []
    if flag.get("killed"):
        on, reason = False, "killed"
    elif tenants and user["tenant"] not in tenants:
        on, reason = False, "tenant"
    elif user["id"] in (flag.get("allow") or []):
        on, reason = True, "allowlist"
    else:
        hit = next((r for r in flag.get("rules") or [] if _rule_matches(r, user.get("attrs") or {})), None)
        if hit is not None:
            on, reason = bool(hit["serve"]), "rule:" + hit["id"]
        else:
            on, reason = bucket < flag.get("rollout_bp", 0), "rollout"
    return {"flag": key, "user": user["id"], "tenant": user["tenant"], "on": on, "reason": reason, "bucket": bucket}


def evaluate_flags(flags, users):
    return [_evaluate(f, u) for f in flags for u in users]
