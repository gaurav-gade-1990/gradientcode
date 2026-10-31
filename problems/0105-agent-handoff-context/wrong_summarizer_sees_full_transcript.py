import copy


def handoff(transcript, specialist, llm):
    # Bug: the summary is generated from the raw triage transcript, so the scratchpad leaks through the summary instead.
    allowed = set(specialist["tools"])
    kept_ids = set()
    carried = []
    for m in transcript:
        role = m["role"]
        if role == "system":
            continue
        if role == "user":
            carried.append(copy.deepcopy(m))
        elif role == "assistant":
            if m.get("private"):
                continue
            m = copy.deepcopy(m)
            if "tool_calls" in m:
                m["tool_calls"] = [tc for tc in m["tool_calls"] if tc["name"] in allowed]
                kept_ids.update(tc["id"] for tc in m["tool_calls"])
                if not m["tool_calls"]:
                    del m["tool_calls"]
            if "tool_calls" not in m and not m.get("content"):
                continue
            carried.append(m)
        elif role == "tool":
            if m["tool_call_id"] in kept_ids:
                carried.append(copy.deepcopy(m))
    prompt = "Summarize this conversation for the " + specialist["name"] + " agent in at most three sentences."
    summary = llm.complete([{"role": "system", "content": prompt}] + list(transcript)).content
    return ([{"role": "system", "content": specialist["system_prompt"]}] + carried
            + [{"role": "system", "content": "Handoff summary from triage: " + summary}])
