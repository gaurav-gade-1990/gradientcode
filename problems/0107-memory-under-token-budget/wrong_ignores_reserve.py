from gc_runtime import message_tokens


def build_context(messages, budget, keep_last, reserve, summarize):
    # Bug: the summary's reserve is not subtracted, so after the summary is added the prompt overflows the budget.
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
    while j >= 0 and used + message_tokens(older[j]) <= budget:
        used += message_tokens(older[j])
        kept.insert(0, older[j])
        j -= 1
    dropped = [m for u in older[:j + 1] for m in u]
    head = [system]
    if dropped:
        head.append({"role": "system", "content": "Summary of earlier conversation: " + summarize(dropped)})
    return head + [m for u in kept + tail for m in u]
