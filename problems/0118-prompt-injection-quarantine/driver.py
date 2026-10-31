def run(ns, rules, steps, approvals, min_len=6):
    """Play a transcript: wrap every tool output, gate every tool call, report what the agent saw and ran."""
    guard = ns["InjectionGuard"](rules, min_len=min_len)
    transcript, decisions, executed = [], [], []
    approved_ids = set(approvals)
    for step in steps:
        if step["type"] == "tool_output":
            transcript.append(guard.wrap(step["id"], step["tool"], step["text"]))
        else:
            d = guard.check_call(step["id"], step["tool"], step["arguments"], step["id"] in approved_ids)
            decisions.append({"id": step["id"], "tool": step["tool"], "decision": d["decision"], "tainted": list(d["tainted"])})
            if d["decision"] in ("allow", "approved"):
                executed.append(step["id"])
    return {"transcript": transcript, "decisions": decisions, "executed": executed}
