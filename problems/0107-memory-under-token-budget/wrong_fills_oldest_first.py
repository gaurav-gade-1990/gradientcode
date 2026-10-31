from gc_runtime import message_tokens


def build_context(messages, budget, keep_last, reserve, summarize):
    # Bug: older turns are added oldest-first. The greeting survives and the turns right before the
    # pinned tail, the ones the user is actually talking about, get summarized.
    system, rest = messages[0], messages[1:]
    units, i = [], 0
    while i < len(rest):
        unit = [rest[i]]
        i += 1
        if unit[0]["role"] == "assistant" and unit[0].get("tool_calls"):
            while i < len(rest) and rest[i]["role"] == "tool":
                unit.append(rest[i])
                i += 1
        units.append(unit)
    cut = max(0, len(units) - keep_last)
    older, tail = units[:cut], units[cut:]
    used = message_tokens([system] + [m for u in tail for m in u])
    j = 0
    while j < len(older) and used + message_tokens(older[j]) <= budget - reserve:
        used += message_tokens(older[j])
        j += 1
    kept, dropped = older[:j], [m for u in older[j:] for m in u]
    head = [system]
    if dropped:
        head.append({"role": "system", "content": "Summary of earlier conversation: " + summarize(dropped)})
    return head + [m for u in kept + tail for m in u]
