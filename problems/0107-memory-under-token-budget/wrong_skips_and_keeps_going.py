from gc_runtime import message_tokens


def build_context(messages, budget, keep_last, reserve, summarize):
    # Bug: a turn that doesn't fit is skipped and the walk continues, so the history has a hole in the middle and the model loses the thread.
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
    kept = []
    j = len(older) - 1
    dropped = []
    while j >= 0:
        if used + message_tokens(older[j]) <= budget - reserve:
            used += message_tokens(older[j])
            kept.insert(0, older[j])
        else:
            dropped = list(older[j]) + dropped
        j -= 1
    head = [system]
    if dropped:
        head.append({"role": "system", "content": "Summary of earlier conversation: " + summarize(dropped)})
    return head + [m for u in kept + tail for m in u]
